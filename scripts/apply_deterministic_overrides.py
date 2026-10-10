# scripts/apply_deterministic_overrides.py
"""Applies line-bounded deterministic criteria overrides across an extraction cache."""
from __future__ import annotations

import argparse
import importlib
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("deterministic_overrides")

# Dynamic import to avoid leading-number syntax issues
_extractor = importlib.import_module("scripts.14_ai_copilot_extractor_v2")
load_parsed_documents = _extractor.load_parsed_documents
build_category_context = _extractor.build_category_context
deterministic_answer = _extractor.deterministic_answer
CAT_PRIMARY_SOURCES = _extractor.CAT_PRIMARY_SOURCES

DETERMINISTIC_TARGETS = {"F_Q1", "F_Q7", "L_Q1", "L_Q14"}


def apply_deterministic_updates(
    src_cache_dir: Path | str,
    dst_cache_dir: Path | str,
    parsed_dir: Path | str,
    allowlist_path: Path | str,
    rubric_path: Path | str,
) -> dict[str, Any]:
    src_cache = Path(src_cache_dir)
    dst_cache = Path(dst_cache_dir)
    parsed_root = Path(parsed_dir)
    dst_cache.mkdir(parents=True, exist_ok=True)

    with open(allowlist_path, "r", encoding="utf-8") as f:
        allowlist_data = json.load(f)
    startup_ids = [row["startup_id"] for row in allowlist_data.get("startups", [])]

    with open(rubric_path, "r", encoding="utf-8") as f:
        rubric = json.load(f)
    rubric_by_qid = {q.get("new_q_id", q.get("q_id")): q for q in rubric}

    overrides_by_qid: dict[str, int] = defaultdict(int)
    overrides_by_startup: dict[str, list[str]] = {}
    total_overrides = 0
    startups_processed = 0

    for sid in startup_ids:
        src_file = src_cache / f"{sid}.json"
        if not src_file.exists():
            logger.warning(f"Source cache missing for {sid}: {src_file}")
            continue

        existing_records = json.loads(src_file.read_text(encoding="utf-8"))
        records_map = {r["q_id"]: r for r in existing_records}

        startup_parsed = parsed_root / sid
        if not startup_parsed.is_dir():
            logger.warning(f"Parsed markdown directory missing for {sid}: {startup_parsed}")
            (dst_cache / f"{sid}.json").write_text(json.dumps(existing_records, indent=2), encoding="utf-8")
            continue

        try:
            docs = load_parsed_documents(startup_parsed)
            contexts = {
                cat: build_category_context(docs, cat)
                for cat in ["F", "L"]
                if cat in CAT_PRIMARY_SOURCES
            }
        except Exception as e:
            logger.warning(f"Error building primary context for {sid}: {e}")
            (dst_cache / f"{sid}.json").write_text(json.dumps(existing_records, indent=2), encoding="utf-8")
            continue

        startup_applied: list[str] = []

        for qid in sorted(DETERMINISTIC_TARGETS):
            q_def = rubric_by_qid.get(qid)
            if not q_def:
                continue
            cat = q_def.get("cat_code") or qid.split("_")[0]
            ctx = contexts.get(cat, {})
            primary_text = ctx.get("primary_text", "")
            has_primary = ctx.get("has_primary", False)

            if not has_primary or not primary_text:
                continue

            det_rec = deterministic_answer(q_def, primary_text, sid)
            if det_rec and det_rec.get("predicted_val") == 1.0 and not det_rec.get("error_code"):
                records_map[qid] = det_rec
                overrides_by_qid[qid] += 1
                startup_applied.append(qid)
                total_overrides += 1

        if startup_applied:
            overrides_by_startup[sid] = startup_applied

        # Write output in exact rubric order
        ordered_records = []
        for q in rubric:
            q_id = q.get("new_q_id", q.get("q_id"))
            if q_id in records_map:
                ordered_records.append(records_map[q_id])

        dst_file = dst_cache / f"{sid}.json"
        dst_file.write_text(json.dumps(ordered_records, indent=2) + "\n", encoding="utf-8")
        startups_processed += 1

    return {
        "startups_processed": startups_processed,
        "total_overrides": total_overrides,
        "overrides_by_qid": dict(overrides_by_qid),
        "overrides_by_startup": overrides_by_startup,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply line-bounded deterministic criteria overrides")
    parser.add_argument("--src-cache", required=True, help="Source extraction cache directory")
    parser.add_argument("--dst-cache", required=True, help="Destination candidate cache directory")
    parser.add_argument("--parsed-dir", required=True, help="Parsed markdown directory (parsed_clean_v4)")
    parser.add_argument("--allowlist", required=True, help="Active startup allowlist JSON")
    parser.add_argument("--rubric", required=True, help="Master rubric JSON")
    args = parser.parse_args()

    stats = apply_deterministic_updates(
        src_cache_dir=args.src_cache,
        dst_cache_dir=args.dst_cache,
        parsed_dir=args.parsed_dir,
        allowlist_path=args.allowlist,
        rubric_path=args.rubric,
    )

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
