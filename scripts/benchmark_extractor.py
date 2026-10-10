# scripts/benchmark_extractor.py
"""Compare an extractor cache directory against human_reviews exports (read-only)."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def compare_cache_to_human(
    cache_dir: Path, human_rows: list[dict[str, Any]], startup_ids: list[str]
) -> dict[str, float]:
    human: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in human_rows:
        if r.get("score") is not None:
            human[(r["startup_id"], r["question_id"])].append(float(r["score"]))

    n_records = withheld = scored = cited = 0
    diffs: list[float] = []
    for sid in startup_ids:
        path = Path(cache_dir) / f"{sid}.json"
        if not path.exists():
            continue
        for rec in json.loads(path.read_text(encoding="utf-8")):
            n_records += 1
            val = rec.get("predicted_val")
            if val is None:
                withheld += 1
                continue
            scored += 1
            if rec.get("citation"):
                cited += 1
            h = human.get((sid, rec["q_id"]))
            if h:
                diffs.append(abs(float(val) - sum(h) / len(h)))

    n_pairs = len(diffs)
    return {
        "n_records": n_records,
        "n_pairs": n_pairs,
        "exact_match": (sum(1 for d in diffs if d < 1e-9) / n_pairs) if n_pairs else 0.0,
        "mae": (sum(diffs) / n_pairs) if n_pairs else 0.0,
        "withheld_rate": withheld / n_records if n_records else 0.0,
        "scored_rate": scored / n_records if n_records else 0.0,
        "cited_rate": cited / n_records if n_records else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--human-json", required=True, help="Output of export_scored_data.py --format json")
    ap.add_argument("--startups", required=True, help="Comma-separated startup ids")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = json.loads(Path(a.human_json).read_text(encoding="utf-8"))
    metrics = compare_cache_to_human(Path(a.cache_dir), rows, a.startups.split(","))
    Path(a.out).write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
