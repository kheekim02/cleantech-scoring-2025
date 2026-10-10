#!/usr/bin/env python3
"""Wave 1 offline hygiene on promoted ai_cache_v5_parsed (no LLM).

- Stamp shadow withholds (null score, null error_code) as NO_EVIDENCE
- Strip scaffolding citations; withhold non-zero rows that cited templates
- Convert junk micro-cites on non-zero scores to WITHHELD_UNGROUNDED
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scorer.schemas import (  # noqa: E402
    is_entity_short_cite,
    is_junk_micro_citation,
    is_scaffolding_citation,
)


def is_zero(score: Any) -> bool:
    return score is not None and round(float(score), 2) == 0.0


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


def hygiene_record(company: str, rec: dict[str, Any], counts: dict[str, int]) -> dict[str, Any]:
    out = dict(rec)
    qid = str(out.get("q_id") or "?")
    score = out.get("predicted_val")
    cite = out.get("citation")
    err = out.get("error_code")
    rationale = out.get("rationale")

    # 1) Shadow withholds → structured NO_EVIDENCE
    if score is None and not err:
        counts["shadow_to_no_evidence"] += 1
        return structured_withhold(qid, "NO_EVIDENCE")

    # 2) Scaffolding citations
    if cite and str(cite).strip() and is_scaffolding_citation(str(cite)):
        counts["scaffolding_cites"] += 1
        if score is not None and not is_zero(score):
            counts["scaffolding_nonzero_withheld"] += 1
            return structured_withhold(qid, "WITHHELD_UNGROUNDED")
        # Zero / null scored scaffolding: drop cite; keep 0.0 with company-local rationale
        # or convert null-score leftovers to NO_EVIDENCE.
        out["citation"] = None
        out["source_pdf"] = None
        out["page_number"] = None
        if score is None:
            counts["scaffolding_null_to_no_evidence"] += 1
            return structured_withhold(qid, "NO_EVIDENCE")
        if is_zero(score):
            out["predicted_val"] = 0.0
            out["confidence"] = 0.0 if out.get("confidence") is None else out.get("confidence")
            out["rationale"] = (
                f"{company} packet has no founder evidence for this criterion "
                f"(template/worksheet text removed)."
            )
            out["error_code"] = None
            counts["scaffolding_zero_cite_stripped"] += 1
            return out

    # 3) Junk / non-entity micro-cites on non-zero scores (< 3 words)
    if cite and str(cite).strip() and score is not None and not is_zero(score):
        words = [w for w in str(cite).split() if w.strip()]
        if len(words) < 3 and (
            is_junk_micro_citation(str(cite)) or not is_entity_short_cite(str(cite))
        ):
            counts["junk_micro_withheld"] += 1
            return structured_withhold(qid, "WITHHELD_UNGROUNDED")

    # Preserve structured withholds / normal rows
    if out.get("predicted_val") is None and out.get("error_code"):
        out["rationale"] = None
        out["citation"] = None
        out["confidence"] = 0.0 if out.get("confidence") is None else out.get("confidence")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Wave 1 offline cache hygiene")
    ap.add_argument(
        "--cache-dir",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed",
    )
    ap.add_argument(
        "--out-report",
        default="/data/scraping/datasets/cto_accelerator/wave1_offline_hygiene.json",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cache = Path(args.cache_dir)
    counts: dict[str, int] = defaultdict(int)
    companies = 0

    for path in sorted(p for p in cache.glob("*.json") if not p.name.endswith(".primary_map.json")):
        company = path.stem
        records = json.loads(path.read_text())
        if not isinstance(records, list):
            counts["bad_files"] += 1
            continue
        companies += 1
        cleaned = [hygiene_record(company, rec, counts) for rec in records]
        counts["records"] += len(cleaned)
        if not args.dry_run:
            tmp = path.with_suffix(".tmp.json")
            tmp.write_text(json.dumps(cleaned, indent=2))
            tmp.replace(path)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cache_dir": str(cache),
        "dry_run": bool(args.dry_run),
        "companies": companies,
        "counts": dict(counts),
    }
    out = Path(args.out_report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
