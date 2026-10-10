#!/usr/bin/env python3
"""Offline scrub of ai_cache_v5_parsed into ai_cache_v5_remediated (no LLM).

Converts engineered clone rationales into structured withholds, copies primary
maps, and emits a remediation_manifest.json of rows that need selective regen.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scorer.schemas import (  # noqa: E402
    is_engineered_rationale,
    is_scaffolding_citation,
    normalize_text,
)

ABSENCE_RE = re.compile(
    r"((?:does|do)\s+not\s+(?:state|mention|provide|include|contain|specify)|"
    r"no\s+(?:mention|evidence|information|discussion)|"
    r"not\s+(?:explicitly\s+)?(?:stated|mentioned|provided)|"
    r"absent|missing\s+from\s+the\s+document|"
    r"provided\s+documents?\s+contain\s+no)",
    re.IGNORECASE,
)

ENGINEERED_ERROR_MAP = [
    ("score based on the cited primary text only", "WITHHELD_UNSUPPORTED_CLAIM"),
    ("evaluation failed or timed out", "TIMEOUT"),
    ("no primary source document", "NO_PRIMARY"),
    ("score withheld:", "WITHHELD_UNGROUNDED"),
]


def is_zero(score: Any) -> bool:
    return score is not None and round(float(score), 2) == 0.0


def engineered_error_code(rationale: str | None) -> str | None:
    if not rationale:
        return None
    norm = " ".join(str(rationale).lower().split())
    for phrase, code in ENGINEERED_ERROR_MAP:
        if phrase in norm:
            return code
    if is_engineered_rationale(rationale):
        return "WITHHELD_UNSUPPORTED_CLAIM"
    return None


def structured_withhold(qid: str, error_code: str) -> dict[str, Any]:
    return {
        "q_id": qid,
        "predicted_val": None,
        "confidence": 0.0,
        "citation": None,
        "source_pdf": None,
        "page_number": None,
        "rationale": None,
        "error_code": error_code,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Offline scrub v5 cache into remediated dir")
    ap.add_argument(
        "--src",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed",
    )
    ap.add_argument(
        "--dst",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_remediated",
    )
    ap.add_argument(
        "--manifest",
        default="/data/scraping/datasets/cto_accelerator/remediation_manifest.json",
    )
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    dst.mkdir(parents=True, exist_ok=True)

    company_files = sorted(p for p in src.glob("*.json") if not p.name.endswith(".primary_map.json"))
    counts = defaultdict(int)
    needs_regen: list[dict[str, str]] = []
    # First pass: load all records for clone indexing after per-file scrub
    scrubbed: dict[str, list[dict[str, Any]]] = {}

    for path in company_files:
        company = path.stem
        records = json.loads(path.read_text())
        if not isinstance(records, list):
            counts["bad_files"] += 1
            continue
        out_recs: list[dict[str, Any]] = []
        for rec in records:
            counts["records_in"] += 1
            qid = str(rec.get("q_id") or "?")
            rationale = rec.get("rationale") or ""
            score = rec.get("predicted_val")
            cite = rec.get("citation")
            code = engineered_error_code(rationale)
            if code:
                out_recs.append(structured_withhold(qid, code))
                counts[f"withhold_{code}"] += 1
                counts["engineered_converted"] += 1
                continue

            # G2.3 → needs regen
            if (
                rationale
                and ABSENCE_RE.search(str(rationale))
                and score is not None
                and round(float(score), 2) >= 0.5
            ):
                counts["g23_flagged"] += 1
                needs_regen.append({"company": company, "q_id": qid, "reason": "g2.3"})
                out_recs.append(dict(rec))
                continue

            # Scaffolding citation stubs → needs regen
            if cite and is_scaffolding_citation(str(cite)):
                counts["scaffolding_cite_flagged"] += 1
                needs_regen.append({"company": company, "q_id": qid, "reason": "scaffolding_cite"})
                out_recs.append(dict(rec))
                continue

            out_recs.append(dict(rec))
            if score is not None:
                counts["scored_kept"] += 1
            else:
                counts["null_kept"] += 1

        scrubbed[company] = out_recs

        # Always copy primary maps (never symlink). Symlinks break if dst is later
        # renamed over src (promote remediated → parsed created self-loops).
        map_src = src / f"{company}.primary_map.json"
        map_dst = dst / f"{company}.primary_map.json"
        if map_src.is_file() and not map_src.is_symlink():
            if map_dst.exists() or map_dst.is_symlink():
                map_dst.unlink()
            shutil.copy2(map_src, map_dst)
            counts["primary_maps"] += 1
        elif map_src.is_symlink():
            # Resolve once into a real file when source itself is a symlink.
            try:
                real = map_src.resolve(strict=True)
                if map_dst.exists() or map_dst.is_symlink():
                    map_dst.unlink()
                shutil.copy2(real, map_dst)
                counts["primary_maps"] += 1
            except OSError:
                counts["missing_primary_maps"] += 1
        else:
            counts["missing_primary_maps"] += 1
        if map_dst.exists() and map_dst.is_symlink():
            raise RuntimeError(
                f"refuse to leave symlink primary_map after copy: {map_dst}"
            )

    # Cross-company exact clone index on non-zero rows (post engineered scrub)
    rat_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    cite_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for company, recs in scrubbed.items():
        for rec in recs:
            score = rec.get("predicted_val")
            if score is None or is_zero(score):
                continue
            qid = str(rec.get("q_id") or "?")
            rat = rec.get("rationale") or ""
            cite = rec.get("citation") or ""
            if rat.strip():
                rat_index[qid].append((company, rat))
            if cite.strip():
                cite_index[qid].append((company, cite))

    clone_keys: set[tuple[str, str]] = set()
    for qid, rows in rat_index.items():
        by_norm: dict[str, list[str]] = defaultdict(list)
        for company, text in rows:
            n = normalize_text(text)
            if len(n) >= 12:
                by_norm[n].append(company)
        for companies in by_norm.values():
            uniq = sorted(set(companies))
            if len(uniq) >= 2:
                for c in uniq:
                    clone_keys.add((c, qid))
                    counts["nonzero_rationale_clone_members"] += 1
    for qid, rows in cite_index.items():
        by_norm = defaultdict(list)
        for company, text in rows:
            n = normalize_text(text)
            if len(n) >= 12:
                by_norm[n].append(company)
        for companies in by_norm.values():
            uniq = sorted(set(companies))
            if len(uniq) >= 2:
                for c in uniq:
                    clone_keys.add((c, qid))
                    counts["nonzero_citation_clone_members"] += 1

    existing = {(r["company"], r["q_id"]) for r in needs_regen}
    for company, qid in sorted(clone_keys):
        if (company, qid) not in existing:
            needs_regen.append({"company": company, "q_id": qid, "reason": "nonzero_clone"})
            counts["clone_flagged"] += 1

    # Write scrubbed company files
    for company, recs in scrubbed.items():
        (dst / f"{company}.json").write_text(json.dumps(recs, indent=2))
        counts["companies_out"] += 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "src": str(src),
        "dst": str(dst),
        "counts": dict(counts),
        "needs_regen_count": len(needs_regen),
        "needs_regen": needs_regen,
        "sample_companies": [
            "CarbonDots",
            "Cero_Global_Holdings",
            "Hubbletek",
            "SOLARSYSTEMS",
            "SPCTA_Industrial",
        ],
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(json.dumps({
        "dst": str(dst),
        "manifest": str(manifest_path),
        "companies": counts["companies_out"],
        "engineered_converted": counts["engineered_converted"],
        "needs_regen": len(needs_regen),
        "primary_maps": counts["primary_maps"],
        "missing_primary_maps": counts["missing_primary_maps"],
        "g23_flagged": counts["g23_flagged"],
        "scaffolding_cite_flagged": counts["scaffolding_cite_flagged"],
        "clone_flagged": counts["clone_flagged"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
