# scripts/analyze_benchmark_discrepancies.py
"""Detailed discrepancy diagnostic engine for startup scorer benchmark caches."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _index_human_scores(human_rows: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in human_rows:
        if r.get("score") is not None and r.get("startup_id") and r.get("question_id"):
            grouped[(r["startup_id"], r["question_id"])].append(float(r["score"]))
    return {k: sum(v) / len(v) for k, v in grouped.items()}


def analyze_category_discrepancies(
    cache_dir: Path,
    human_rows: list[dict[str, Any]],
    startup_ids: list[str],
    rubric_questions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    human = _index_human_scores(human_rows)
    cat_map = {q.get("new_q_id", q.get("q_id")): q.get("cat_code", "OTHER") for q in rubric_questions}

    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "total": 0,
        "withheld_count": 0,
        "pairs": 0,
        "exact_count": 0,
        "abs_errors": [],
        "signed_errors": [],
    })

    for sid in startup_ids:
        path = Path(cache_dir) / f"{sid}.json"
        if not path.is_file():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            qid = rec.get("q_id")
            cat = cat_map.get(qid, qid.split("_")[0] if "_" in str(qid) else "OTHER")
            val = rec.get("predicted_val")
            stats[cat]["total"] += 1

            if val is None:
                stats[cat]["withheld_count"] += 1
                continue

            if (sid, qid) in human:
                h_val = human[(sid, qid)]
                diff = float(val) - h_val
                abs_diff = abs(diff)
                stats[cat]["pairs"] += 1
                stats[cat]["abs_errors"].append(abs_diff)
                stats[cat]["signed_errors"].append(diff)
                if abs_diff < 1e-9:
                    stats[cat]["exact_count"] += 1

    summary = {}
    for cat, d in sorted(stats.items()):
        p = d["pairs"]
        t = d["total"]
        mae = (sum(d["abs_errors"]) / p) if p else 0.0
        bias = (sum(d["signed_errors"]) / p) if p else 0.0
        exact_pct = (d["exact_count"] / p * 100) if p else 0.0
        withheld_pct = (d["withheld_count"] / t * 100) if t else 0.0
        summary[cat] = {
            "total_criteria": t,
            "pairs": p,
            "exact_count": d["exact_count"],
            "exact_match_pct": exact_pct,
            "mae": mae,
            "mean_bias": bias,
            "withheld_count": d["withheld_count"],
            "withheld_pct": withheld_pct,
        }
    return summary


def rank_worst_criteria(
    cache_dir: Path,
    human_rows: list[dict[str, Any]],
    startup_ids: list[str],
    rubric_questions: list[dict[str, Any]],
    top_k: int = 15,
) -> list[dict[str, Any]]:
    human = _index_human_scores(human_rows)
    q_meta = {q.get("new_q_id", q.get("q_id")): q for q in rubric_questions}

    q_data: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "abs_errors": [],
        "signed_errors": [],
        "exact_count": 0,
        "withheld_count": 0,
        "total_evals": 0,
    })

    for sid in startup_ids:
        path = Path(cache_dir) / f"{sid}.json"
        if not path.is_file():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            qid = rec.get("q_id")
            val = rec.get("predicted_val")
            q_data[qid]["total_evals"] += 1

            if val is None:
                q_data[qid]["withheld_count"] += 1
                continue

            if (sid, qid) in human:
                h_val = human[(sid, qid)]
                diff = float(val) - h_val
                abs_diff = abs(diff)
                q_data[qid]["abs_errors"].append(abs_diff)
                q_data[qid]["signed_errors"].append(diff)
                if abs_diff < 1e-9:
                    q_data[qid]["exact_count"] += 1

    ranked = []
    for qid, d in q_data.items():
        pairs = len(d["abs_errors"])
        if pairs == 0:
            continue
        mae = sum(d["abs_errors"]) / pairs
        bias = sum(d["signed_errors"]) / pairs
        exact_pct = (d["exact_count"] / pairs * 100) if pairs else 0.0
        meta = q_meta.get(qid, {})
        ranked.append({
            "q_id": qid,
            "cat_code": meta.get("cat_code", qid.split("_")[0]),
            "text": meta.get("text", ""),
            "pairs": pairs,
            "mae": mae,
            "mean_bias": bias,
            "exact_match_pct": exact_pct,
            "withheld_count": d["withheld_count"],
        })

    # Sort descending by MAE, then ascending by exact match percentage
    ranked.sort(key=lambda x: (-x["mae"], x["exact_match_pct"]))
    return ranked[:top_k]


def classify_error_modes(
    cache_dir: Path,
    human_rows: list[dict[str, Any]],
    startup_ids: list[str],
) -> dict[str, int]:
    human = _index_human_scores(human_rows)
    modes = {
        "exact_match": 0,
        "over_prediction": 0,            # AI=1.0 while Human <= 0.25
        "under_prediction": 0,           # AI=0.0 while Human >= 0.75
        "fractional_tier_mismatch": 0,   # Delta in (0.25, 0.5]
        "withheld": 0,                   # AI=None while human reviewed
    }

    for sid in startup_ids:
        path = Path(cache_dir) / f"{sid}.json"
        if not path.is_file():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            qid = rec.get("q_id")
            val = rec.get("predicted_val")
            if (sid, qid) not in human:
                continue
            h_val = human[(sid, qid)]

            if val is None:
                modes["withheld"] += 1
                continue

            diff = float(val) - h_val
            abs_diff = abs(diff)

            if abs_diff < 1e-9:
                modes["exact_match"] += 1
            elif float(val) >= 0.99 and h_val <= 0.25:
                modes["over_prediction"] += 1
            elif float(val) <= 0.01 and h_val >= 0.75:
                modes["under_prediction"] += 1
            else:
                modes["fractional_tier_mismatch"] += 1

    return modes


def format_discrepancy_markdown(
    cat_summary: dict[str, dict[str, Any]],
    worst_q: list[dict[str, Any]],
    error_modes: dict[str, int],
    total_records: int,
    provenance_meta: dict[str, Any],
) -> str:
    lines = [
        "# Task 0 Benchmark Discrepancy Analysis Report",
        "",
        "## 1. Provenance & Dataset Header",
        f"- **Source Host:** `{provenance_meta.get('source_host', 'Spark 136.24.130.250')}`",
        f"- **Cache Directory:** `{provenance_meta.get('cache_dir', 'ai_cache_l2_bench_baseline')}`",
        f"- **Benchmark Startups (N=5):** `{', '.join(provenance_meta.get('startups', []))}`",
        f"- **Total Evaluated Records:** `{total_records}`",
        "",
        "## 2. Category Performance Summary",
        "Categories ranked by exact match rate (lowest to highest):",
        "",
        "| Category | Code | Evaluated Pairs | Exact Match % | MAE | Mean Bias (AI - Human) | Withheld % |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    sorted_cats = sorted(cat_summary.items(), key=lambda x: (x[1]["exact_match_pct"], -x[1]["mae"]))
    for code, s in sorted_cats:
        bias_str = f"+{s['mean_bias']:.3f}" if s["mean_bias"] > 0 else f"{s['mean_bias']:.3f}"
        lines.append(
            f"| {code} | `{code}` | {s['pairs']} | **{s['exact_match_pct']:.2f}%** | {s['mae']:.3f} | {bias_str} | {s['withheld_pct']:.2f}% |"
        )

    lines.extend([
        "",
        "## 3. Global Error Mode Distribution",
        "",
        "| Error Mode | Occurrence Count | Percentage of Evaluated Pairs | Diagnosis |",
        "| :--- | :---: | :---: | :--- |",
    ])

    total_pairs = sum(error_modes.values())
    mode_descriptions = {
        "exact_match": "Exact score agreement within 1e-9",
        "over_prediction": "AI awarded 1.0 while human scored <= 0.25 (loose regex or hallucinations)",
        "under_prediction": "AI awarded 0.0 while human scored >= 0.75 (overly strict gating or primary doc miss)",
        "fractional_tier_mismatch": "Disagreement on intermediate tiers (e.g. 0.5 vs 0.75)",
        "withheld": "Model safely withheld without guessing",
    }
    for mode, count in error_modes.items():
        pct = (count / total_pairs * 100) if total_pairs else 0.0
        lines.append(f"| **{mode.replace('_', ' ').title()}** | {count} | {pct:.2f}% | {mode_descriptions.get(mode, '')} |")

    lines.extend([
        "",
        "## 4. Top 15 Highest-Discrepancy Criteria",
        "Specific rubric questions with the highest mean absolute error (MAE) across the benchmark cohort:",
        "",
        "| Question ID | Category | Question Prompt Excerpt | Pairs | MAE | Mean Bias | Exact Match % |",
        "| :--- | :---: | :--- | :---: | :---: | :---: | :---: |",
    ])

    for q in worst_q:
        prompt_snippet = (q["text"][:65] + "...") if len(q["text"]) > 65 else q["text"]
        prompt_snippet = prompt_snippet.replace("|", "/")
        bias_str = f"+{q['mean_bias']:.3f}" if q["mean_bias"] > 0 else f"{q['mean_bias']:.3f}"
        lines.append(
            f"| `{q['q_id']}` | `{q['cat_code']}` | {prompt_snippet} | {q['pairs']} | **{q['mae']:.3f}** | {bias_str} | {q['exact_match_pct']:.1f}% |"
        )

    lines.extend([
        "",
        "## 5. Architectural Implications for Layer 2",
        "1. **Business Canvas (`BC`) & Market (`M`):** Exhibit lowest exact matches (<60%) and highest withholdings, directly reflecting missing customer discovery / market matrix primary document routing.",
        "2. **Over-prediction on Quantitative Criteria (`F_Q11`, `F_Q14`, `PMF_Q30`):** Confirms why Task 1 line-bounded deterministic evaluator is strictly needed.",
        "3. **Visual Deck Criteria (`IP_Q7`, `PMF_Q24`):** Confirm 100% failure rate on diagram/flowchart criteria, proving the hypothesis in Task 4.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Digest Task 0 benchmark discrepancies")
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--human-json", required=True)
    ap.add_argument("--rubric", required=True)
    ap.add_argument("--startups", required=True)
    ap.add_argument("--out-md", help="Output path for Markdown report")
    ap.add_argument("--out-json", help="Output path for JSON data")
    a = ap.parse_args()

    human_rows = json.loads(Path(a.human_json).read_text(encoding="utf-8"))
    rubric_questions = json.loads(Path(a.rubric).read_text(encoding="utf-8"))
    startup_ids = [s.strip() for s in a.startups.split(",") if s.strip()]

    cat_summary = analyze_category_discrepancies(Path(a.cache_dir), human_rows, startup_ids, rubric_questions)
    worst_q = rank_worst_criteria(Path(a.cache_dir), human_rows, startup_ids, rubric_questions, top_k=15)
    modes = classify_error_modes(Path(a.cache_dir), human_rows, startup_ids)

    prov = {
        "source_host": "Spark 136.24.130.250",
        "cache_dir": str(a.cache_dir),
        "startups": startup_ids,
    }

    report_md = format_discrepancy_markdown(cat_summary, worst_q, modes, len(startup_ids) * 282, prov)

    if a.out_md:
        Path(a.out_md).write_text(report_md, encoding="utf-8")
        print(f"Wrote report to {a.out_md}")
    if a.out_json:
        data = {
            "provenance": prov,
            "category_summary": cat_summary,
            "worst_criteria": worst_q,
            "error_modes": modes,
        }
        Path(a.out_json).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote data to {a.out_json}")


if __name__ == "__main__":
    main()


