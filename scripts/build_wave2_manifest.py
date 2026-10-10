#!/usr/bin/env python3
"""Build Wave 2 selective regen manifest from promoted ai_cache_v5_parsed.

Targets:
- All ES_Q1 rows with WITHHELD_UNSUPPORTED_CLAIM / WITHHELD_UNGROUNDED / null score
- Scaffolding nonzero losses (Vaanelai IS_Q17/IS_Q21 class): WITHHELD_UNGROUNDED on
  IS_Q17/IS_Q21 when company previously had Markets-template cites
- Optional: top N short non-zero rationales (G2.1) — capped, default 0
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Wave 2 regen manifest")
    ap.add_argument(
        "--cache-dir",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed",
    )
    ap.add_argument(
        "--out",
        default="/data/scraping/datasets/cto_accelerator/wave2_regen_manifest.json",
    )
    ap.add_argument(
        "--g21-cap",
        type=int,
        default=0,
        help="Optional cap of short non-zero rationale rows to include (0=skip)",
    )
    args = ap.parse_args()

    cache = Path(args.cache_dir)
    needs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    reasons: Counter[str] = Counter()

    def add(company: str, qid: str, reason: str) -> None:
        key = (company, qid)
        if key in seen:
            return
        seen.add(key)
        needs.append({"company": company, "q_id": qid, "reason": reason})
        reasons[reason] += 1

    g21_candidates: list[tuple[int, str, str]] = []

    for path in sorted(cache.glob("*.json")):
        if path.name.endswith(".primary_map.json"):
            continue
        company = path.stem
        try:
            records = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(records, list):
            continue
        for rec in records:
            qid = str(rec.get("q_id") or "")
            ec = rec.get("error_code")
            score = rec.get("predicted_val")
            rat = (rec.get("rationale") or "").strip()

            if qid == "ES_Q1":
                if ec in {
                    "WITHHELD_UNSUPPORTED_CLAIM",
                    "WITHHELD_UNGROUNDED",
                    "NO_EVIDENCE",
                }:
                    add(company, qid, f"es_q1:{ec}")
                elif score is None and not ec:
                    add(company, qid, "es_q1:null_null")

            # Wave1 scaffolding nonzero losses (Markets template → withhold)
            if qid in {"IS_Q17", "IS_Q21"} and ec == "WITHHELD_UNGROUNDED":
                add(company, qid, "scaffolding_nonzero_loss")

            if (
                args.g21_cap > 0
                and score is not None
                and round(float(score), 2) != 0.0
                and ec is None
                and rat
            ):
                words = len(rat.split())
                if words < 8:
                    g21_candidates.append((words, company, qid))

    g21_candidates.sort()
    for _, company, qid in g21_candidates[: args.g21_cap]:
        add(company, qid, "g21_short_rationale")

    by_company: Counter[str] = Counter(r["company"] for r in needs)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "wave": "2",
        "cache_dir": str(cache),
        "needs_regen_count": len(needs),
        "needs_regen": needs,
        "reason_counts": dict(reasons),
        "companies": len(by_company),
        "sample_companies": [
            "Vaanelai",
            "H2O_Now",
            "CarbonDots",
            "AmpTrans",
            "Curve_Control",
        ],
        "g21_cap": args.g21_cap,
    }
    out = Path(args.out)
    out.write_text(json.dumps(payload, indent=2))
    print(
        json.dumps(
            {
                "out": str(out),
                "needs_regen_count": len(needs),
                "companies": len(by_company),
                "reason_counts": dict(reasons),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
