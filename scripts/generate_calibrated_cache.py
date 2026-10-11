# scripts/generate_calibrated_cache.py
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collections import defaultdict
from src.scorer.schemas import normalize_text
from src.scorer.score_calibrator import calibrate_record
from src.scorer.visual_deck_inspector import inspect_deck_visuals
from src.scorer.deterministic_evaluator import evaluate_visual_criterion
from scripts.docling_ingestion import detect_doc_type

logger = logging.getLogger("generate_calibrated_cache")


def generate_calibrated_cache(
    src_cache_dir: Path | str,
    dst_cache_dir: Path | str,
    raw_dir: Path | str,
    allowlist_path: Path | str,
    rubric_path: Path | str,
    calibrate_fractional: bool = False,
) -> dict[str, Any]:
    src = Path(src_cache_dir)
    dst = Path(dst_cache_dir)
    raw = Path(raw_dir)
    dst.mkdir(parents=True, exist_ok=True)

    allowlist = json.loads(Path(allowlist_path).read_text(encoding="utf-8"))
    rubric = json.loads(Path(rubric_path).read_text(encoding="utf-8"))
    rubric_map = {q.get("new_q_id", q.get("q_id")): q for q in rubric}
    startup_ids = [s["startup_id"] for s in allowlist.get("startups", [])]

    # Pre-scan cohort to identify shared/clone citations and rationales
    cite_by_qid_counts: dict[tuple[str, str], int] = defaultdict(int)
    rat_by_qid_counts: dict[tuple[str, str], int] = defaultdict(int)
    for sid in startup_ids:
        src_path = src / f"{sid}.json"
        if not src_path.exists():
            continue
        try:
            records = json.loads(src_path.read_text(encoding="utf-8"))
            for rec in records:
                qid = rec.get("q_id")
                c = normalize_text(str(rec.get("citation") or ""))
                r = normalize_text(str(rec.get("rationale") or ""))
                if c:
                    cite_by_qid_counts[(qid, c)] += 1
                if r:
                    rat_by_qid_counts[(qid, r)] += 1
        except Exception as e:
            logger.warning(f"Error pre-scanning {sid}: {e}")

    calibrated_count = 0
    visual_override_count = 0

    for sid in startup_ids:
        src_path = src / f"{sid}.json"
        if not src_path.exists():
            continue
        records = json.loads(src_path.read_text(encoding="utf-8"))
        records_map = {r["q_id"]: r for r in records}

        # Load primary map for verbatim citation grounding and audit compatibility
        pmap: dict[str, Any] = {}
        src_map_path = src / f"{sid}.primary_map.json"
        if src_map_path.exists():
            try:
                pmap = json.loads(src_map_path.read_text(encoding="utf-8"))
                (dst / f"{sid}.primary_map.json").write_text(
                    json.dumps(pmap, indent=2) + "\n", encoding="utf-8"
                )
            except Exception as e:
                logger.warning(f"Error reading/copying primary_map for {sid}: {e}")

        # Visual deck inspection if raw deck exists
        deck_pdf = None
        co_raw = raw / sid
        if co_raw.is_dir():
            for p in sorted(co_raw.rglob("*.pdf")):
                if detect_doc_type(p.name) == "EBD8":
                    deck_pdf = p
                    break

        deck_meta = None
        if deck_pdf and deck_pdf.exists():
            try:
                deck_meta = inspect_deck_visuals(deck_pdf)
            except Exception as e:
                logger.warning(f"Error inspecting deck visuals for {sid}: {e}")

        for qid, rec in list(records_map.items()):
            q_def = rubric_map.get(qid)
            if not q_def:
                continue

            # Visual criteria check strictly for IP_Q7 (pitch deck primary)
            if qid == "IP_Q7" and deck_meta:
                ip_primary = pmap.get("IP", "")
                vis_rec = evaluate_visual_criterion(
                    qid, deck_meta, startup_id=sid, primary_text=ip_primary
                )
                if vis_rec and vis_rec.get("predicted_val") == 1.0:
                    records_map[qid] = vis_rec
                    visual_override_count += 1
                    continue

            # Layer 3 Fractional calibration (if enabled and citation & rationale are unique across the cohort)
            if calibrate_fractional:
                norm_c = normalize_text(str(rec.get("citation") or ""))
                norm_r = normalize_text(str(rec.get("rationale") or ""))
                if (
                    cite_by_qid_counts.get((qid, norm_c), 0) <= 1
                    and rat_by_qid_counts.get((qid, norm_r), 0) <= 1
                ):
                    cal = calibrate_record(rec, q_def)
                    if cal.get("calibrated"):
                        records_map[qid] = cal
                        calibrated_count += 1

        # Preserve exact rubric order
        ordered = [
            records_map[q.get("new_q_id", q.get("q_id"))]
            for q in rubric
            if q.get("new_q_id", q.get("q_id")) in records_map
        ]
        (dst / f"{sid}.json").write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")

    return {
        "startups_processed": len(startup_ids),
        "calibrated_count": calibrated_count,
        "visual_override_count": visual_override_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Layer 3 Calibrated & Visual Extraction Cache")
    parser.add_argument("--src-cache", required=True)
    parser.add_argument("--dst-cache", required=True)
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--allowlist", required=True)
    parser.add_argument("--rubric", required=True)
    parser.add_argument(
        "--calibrate-fractional",
        action="store_true",
        default=False,
        help="Enable experimental fractional score calibration",
    )
    args = parser.parse_args()

    stats = generate_calibrated_cache(
        args.src_cache,
        args.dst_cache,
        args.raw_dir,
        args.allowlist,
        args.rubric,
        calibrate_fractional=args.calibrate_fractional,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
