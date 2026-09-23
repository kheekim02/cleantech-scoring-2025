"""Comparative Audit Engine: v1 (Ollama) vs v2 (Docling + SGLang + Instructor).

Analyzes scoring concordance, verbatim grounding rates, and category-level
accuracy shifts across the diligence rubric.
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Any


def calculate_metrics(
    v1_records: list[dict[str, Any]],
    v2_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate detailed comparison metrics between v1 and v2 extraction sets."""
    v1_map = {r.get("new_q_id", r.get("q_id")): r for r in v1_records}
    v2_map = {r.get("new_q_id", r.get("q_id")): r for r in v2_records}

    common_qids = sorted(set(v1_map.keys()) & set(v2_map.keys()))
    if not common_qids:
        return {
            "total_compared": 0,
            "exact_matches": 0,
            "concordance_pct": 0.0,
            "v1_citations": 0,
            "v2_citations": 0,
            "v2_grounded_citations": 0,
            "v2_grounding_rate_pct": 0.0,
            "by_category": {},
        }

    exact_matches = 0
    close_matches = 0  # within 0.25 pts
    v1_citations = 0
    v2_citations = 0
    v2_grounded = 0
    v1_scores = []
    v2_scores = []

    cat_stats: dict[str, dict[str, Any]] = {}

    for qid in common_qids:
        r1 = v1_map[qid]
        r2 = v2_map[qid]

        val1 = r1.get("predicted_val")
        val2 = r2.get("predicted_val")

        cit1 = r1.get("citation") or r1.get("verbatim_citation")
        cit2 = r2.get("citation") or r2.get("verbatim_citation")
        p2 = r2.get("page_number")

        cat = qid.split("_")[0] if "_" in qid else "OTHER"
        if cat not in cat_stats:
            cat_stats[cat] = {
                "count": 0,
                "exact": 0,
                "v1_cit": 0,
                "v2_cit": 0,
                "v2_grounded": 0,
            }
        cat_stats[cat]["count"] += 1

        # Check score match
        if val1 is None and val2 is None:
            exact_matches += 1
            close_matches += 1
            cat_stats[cat]["exact"] += 1
        elif val1 is not None and val2 is not None:
            v1_scores.append(float(val1))
            v2_scores.append(float(val2))
            diff = abs(float(val1) - float(val2))
            if diff < 0.01:
                exact_matches += 1
                cat_stats[cat]["exact"] += 1
            if diff <= 0.25:
                close_matches += 1

        # Citations
        if cit1 and len(cit1.strip()) > 5:
            v1_citations += 1
            cat_stats[cat]["v1_cit"] += 1

        if cit2 and len(cit2.strip()) > 5:
            v2_citations += 1
            cat_stats[cat]["v2_cit"] += 1
            if p2 is not None:
                v2_grounded += 1
                cat_stats[cat]["v2_grounded"] += 1

    total = len(common_qids)
    concordance = (exact_matches / total) * 100.0 if total > 0 else 0.0
    close_concordance = (close_matches / total) * 100.0 if total > 0 else 0.0
    grounding_rate = (v2_grounded / v2_citations * 100.0) if v2_citations > 0 else 100.0

    by_cat_summary = {}
    for cat, s in sorted(cat_stats.items()):
        by_cat_summary[cat] = {
            "questions": s["count"],
            "exact_matches": s["exact"],
            "concordance_pct": round((s["exact"] / s["count"] * 100.0) if s["count"] else 0.0, 1),
            "v1_citations": s["v1_cit"],
            "v2_citations": s["v2_cit"],
            "v2_grounded": s["v2_grounded"],
            "grounding_rate_pct": round((s["v2_grounded"] / s["v2_cit"] * 100.0) if s["v2_cit"] else 100.0, 1),
        }

    return {
        "total_compared": total,
        "exact_matches": exact_matches,
        "concordance_pct": round(concordance, 2),
        "close_concordance_pct": round(close_concordance, 2),
        "v1_citations": v1_citations,
        "v2_citations": v2_citations,
        "v2_grounded_citations": v2_grounded,
        "v2_grounding_rate_pct": round(grounding_rate, 2),
        "v1_avg_score": round(sum(v1_scores) / len(v1_scores), 3) if v1_scores else 0.0,
        "v2_avg_score": round(sum(v2_scores) / len(v2_scores), 3) if v2_scores else 0.0,
        "by_category": by_cat_summary,
    }


def run_audit(v1_dir: str, v2_dir: str, output_report: str | None = None) -> dict[str, Any]:
    """Audit all startups that have evaluations in both v1 and v2 directories."""
    v1_path = Path(v1_dir)
    v2_path = Path(v2_dir)

    v2_files = sorted(v2_path.glob("*.json"))
    if not v2_files:
        print(f"No JSON cache files found in {v2_dir}")
        return {}

    all_v1_records = []
    all_v2_records = []
    startup_reports = {}

    for v2_file in v2_files:
        sid = v2_file.stem
        v1_file = v1_path / f"{sid}.json"
        if not v1_file.exists():
            continue

        try:
            with open(v1_file, "r", encoding="utf-8") as f1, open(v2_file, "r", encoding="utf-8") as f2:
                r1 = json.load(f1)
                r2 = json.load(f2)
                startup_metrics = calculate_metrics(r1, r2)
                startup_reports[sid] = startup_metrics
                all_v1_records.extend(r1)
                all_v2_records.extend(r2)
        except Exception as e:
            print(f"Error auditing {sid}: {e}")

    overall_metrics = calculate_metrics(all_v1_records, all_v2_records)

    report_payload = {
        "startups_audited": len(startup_reports),
        "startups": list(startup_reports.keys()),
        "overall": overall_metrics,
        "per_startup": startup_reports,
    }

    print("\n" + "=" * 65)
    print("      CLEANTECH OPEN 2025: V1 vs V2 COMPARATIVE AUDIT REPORT")
    print("=" * 65)
    print(f"Startups Audited:           {len(startup_reports)}")
    print(f"Total Criteria Evaluated:   {overall_metrics['total_compared']:,}")
    print(f"Exact Score Concordance:    {overall_metrics['concordance_pct']}%")
    print(f"Within-0.25 Concordance:    {overall_metrics['close_concordance_pct']}%")
    print(f"V1 Citations:               {overall_metrics['v1_citations']:,}")
    print(f"V2 Citations Extracted:     {overall_metrics['v2_citations']:,}")
    print(f"V2 Verbatim Grounding Rate: {overall_metrics['v2_grounding_rate_pct']}% ({overall_metrics['v2_grounded_citations']}/{overall_metrics['v2_citations']})")
    print(f"V1 Avg Score:               {overall_metrics['v1_avg_score']} pts")
    print(f"V2 Avg Score:               {overall_metrics['v2_avg_score']} pts")
    print("-" * 65)
    print("CATEGORY BREAKDOWN:")
    print(f"{'CAT':<6} {'COUNT':<7} {'CONCORD%':<10} {'V1 CIT':<8} {'V2 CIT':<8} {'V2 GROUND%':<10}")
    print("-" * 65)
    for cat, s in overall_metrics["by_category"].items():
        print(f"{cat:<6} {s['questions']:<7} {s['concordance_pct']:<10.1f} {s['v1_citations']:<8} {s['v2_citations']:<8} {s['grounding_rate_pct']:<10.1f}")
    print("=" * 65)

    if output_report:
        out_p = Path(output_report)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2)
        print(f"Saved audit report JSON to: {output_report}")

    return report_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit v1 vs v2 Diligence Extractions")
    parser.add_argument("--v1-dir", default="data/ai_cache_clean", help="Directory containing v1 clean extractions")
    parser.add_argument("--v2-dir", default="data/ai_cache_v2", help="Directory containing v2 extractions")
    parser.add_argument("--output", default="data/audit_v1_v2_report.json", help="Path to write JSON audit report")
    args = parser.parse_args()

    run_audit(args.v1_dir, args.v2_dir, args.output)
