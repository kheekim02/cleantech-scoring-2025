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
