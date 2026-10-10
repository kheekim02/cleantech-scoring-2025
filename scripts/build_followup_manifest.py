#!/usr/bin/env python3
"""Build follow-up needs_regen manifest from independent audit HARD findings."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    audit_path = Path(sys.argv[1] if len(sys.argv) > 1 else
                      "/data/scraping/datasets/cto_accelerator/citation_independent_audit_remediated.json")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else
                    "/data/scraping/datasets/cto_accelerator/remediation_manifest_followup.json")
    rep = json.loads(audit_path.read_text())
    rows = []
    seen = set()
    buckets = (
        rep.get("hard_samples", [])
        + rep.get("top_citation_clones", [])
        + rep.get("top_rationale_clones", [])
    )
    for finding in buckets:
        if finding.get("severity") != "HARD":
            continue
        gate = finding.get("gate")
        qid = finding.get("q_id")
        if qid == "*":
            continue
        companies = finding.get("extra", {}).get("companies")
        if not companies:
            companies = [c for c in str(finding.get("company", "")).split(",") if c]
        for company in companies:
            key = (company, qid)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"company": company, "q_id": qid, "reason": f"followup_{gate}"})
    payload = {"needs_regen": rows, "needs_regen_count": len(rows)}
    out_path.write_text(json.dumps(payload, indent=2))
    print(json.dumps({
        "out": str(out_path),
        "followup": len(rows),
        "companies": len({r["company"] for r in rows}),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
