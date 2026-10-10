#!/usr/bin/env python3
"""Selectively regenerate needs_regen rows into ai_cache_v5_remediated.

Uses the fixed accept path in 14_ai_copilot_extractor_v2.py. Resume-safe.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_extractor():
    path = ROOT / "scripts" / "14_ai_copilot_extractor_v2.py"
    spec = importlib.util.spec_from_file_location("extractor_v2_remediation", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description="Selective regen of remediation needs_regen rows")
    ap.add_argument(
        "--cache-dir",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_remediated",
    )
    ap.add_argument(
        "--manifest",
        default="/data/scraping/datasets/cto_accelerator/remediation_manifest.json",
    )
    ap.add_argument(
        "--parsed-dir",
        default="/data/scraping/datasets/cto_accelerator/parsed_clean_v4",
    )
    ap.add_argument(
        "--rubric",
        default="/data/scraping/datasets/cto_accelerator/master_282_rubric.json",
    )
    ap.add_argument("--endpoint", default="http://127.0.0.1:11435")
    ap.add_argument("--model", required=True)
    ap.add_argument(
        "--companies",
        default="",
        help="Comma-separated company filter; empty = all needs_regen companies",
    )
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument(
        "--progress",
        default="/data/scraping/logs/regen_remediation_progress.json",
    )
    args = ap.parse_args()

    ext = load_extractor()
    cache = Path(args.cache_dir)
    manifest = json.loads(Path(args.manifest).read_text())
    needs = manifest.get("needs_regen") or []
    filter_cos = {c.strip() for c in args.companies.split(",") if c.strip()}
    if filter_cos:
        needs = [r for r in needs if r["company"] in filter_cos]

    by_company: dict[str, set[str]] = defaultdict(set)
    for row in needs:
        by_company[row["company"]].add(row["q_id"])

    # Load rubric once
    rubric_path = Path(args.rubric)
    if not rubric_path.is_file():
        alt = ROOT / "master_282_rubric.json"
        rubric_path = alt if alt.is_file() else rubric_path
    rubric = json.loads(rubric_path.read_text())
    questions = {
        (q.get("new_q_id") or q.get("q_id")): q
        for q in rubric
        if (q.get("new_q_id") or q.get("q_id"))
    }

    progress: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "companies": {},
        "done": 0,
        "failed": 0,
    }
    prog_path = Path(args.progress)
    prog_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        inst_client = ext.create_instructor_client(args.endpoint, timeout=60)
    except Exception:
        inst_client = None

    for company, qids in sorted(by_company.items()):
        cache_file = cache / f"{company}.json"
        if not cache_file.is_file():
            print(json.dumps({"skip": company, "reason": "missing_cache"}))
            continue
        records = json.loads(cache_file.read_text())
        by_qid = {str(r.get("q_id")): r for r in records}

        docs = ext.load_parsed_documents(Path(args.parsed_dir) / company)
        if not docs:
            print(json.dumps({"skip": company, "reason": "no_parsed"}))
            continue
        doc_manifest = ext.build_doc_manifest_from_docs(docs)
        category_contexts = {
            cat: ext.build_category_context_from_docs(docs, cat)
            for cat in ext.CAT_PRIMARY_SOURCES
        }

        company_done = 0
        company_fail = 0

        def peer_rationale(qid: str, exclude: str) -> set[str]:
            from src.scorer.schemas import normalize_text
            norms: set[str] = set()
            for path in cache.glob("*.json"):
                if path.name.endswith(".primary_map.json"):
                    continue
                other = path.stem
                if other == exclude:
                    continue
                try:
                    recs = json.loads(path.read_text())
                except Exception:
                    continue
                if not isinstance(recs, list):
                    continue
                for rec in recs:
                    if str(rec.get("q_id")) != qid:
                        continue
                    score = rec.get("predicted_val")
                    if score is None or round(float(score), 2) == 0.0:
                        continue
                    rat = (rec.get("rationale") or "").strip()
                    if rat:
                        norms.add(normalize_text(rat))
            return norms

        def peer_citation(qid: str, exclude: str) -> set[str]:
            from src.scorer.schemas import normalize_text
            norms: set[str] = set()
            for path in cache.glob("*.json"):
                if path.name.endswith(".primary_map.json"):
                    continue
                other = path.stem
                if other == exclude:
                    continue
                try:
                    recs = json.loads(path.read_text())
                except Exception:
                    continue
                if not isinstance(recs, list):
                    continue
                for rec in recs:
                    if str(rec.get("q_id")) != qid:
                        continue
                    score = rec.get("predicted_val")
                    if score is None or round(float(score), 2) == 0.0:
                        continue
                    cite = (rec.get("citation") or "").strip()
                    if cite and len(normalize_text(cite)) >= 12:
                        norms.add(normalize_text(cite))
            return norms

        for qid in sorted(qids):
            q = questions.get(qid)
            if not q:
                company_fail += 1
                continue
            cat = q.get("cat_code") or ""
            ctx = category_contexts.get(cat) or {}
            primary_text = ctx.get("primary_text", "")
            try:
                raw = ext.query_sglang_question(
                    inst_client,
                    args.model,
                    ctx.get("text", ""),
                    q,
                    args.timeout,
                    doc_manifest,
                    ctx.get("has_primary", False),
                    args.endpoint,
                    startup_id=company,
                    temperature=0.0,
                )
                accepted = ext.accept_model_answer(raw, primary_text, q, company=company)
                if accepted.get("error_code") in ext.RETRYABLE_ERROR_CODES:
                    raw2 = ext.query_sglang_question(
                        inst_client,
                        args.model,
                        ctx.get("text", ""),
                        q,
                        args.timeout,
                        doc_manifest,
                        ctx.get("has_primary", False),
                        args.endpoint,
                        startup_id=company,
                        temperature=0.2,
                    )
                    accepted = ext.accept_model_answer(raw2, primary_text, q, company=company)

                # Cross-company uniqueness on rationale and citation for non-zero scores.
                from src.scorer.schemas import normalize_text
                score = accepted.get("predicted_val")
                rat = (accepted.get("rationale") or "").strip()
                cite = (accepted.get("citation") or "").strip()
                clone_hit = False
                if score is not None and round(float(score), 2) != 0.0:
                    if rat and normalize_text(rat) in peer_rationale(qid, company):
                        clone_hit = True
                    if cite and len(normalize_text(cite)) >= 12 and normalize_text(cite) in peer_citation(qid, company):
                        clone_hit = True
                if clone_hit:
                    raw3 = ext.query_sglang_question(
                        inst_client,
                        args.model,
                        ctx.get("text", ""),
                        q,
                        args.timeout,
                        doc_manifest,
                        ctx.get("has_primary", False),
                        args.endpoint,
                        startup_id=company,
                        temperature=0.2,
                    )
                    accepted = ext.accept_model_answer(raw3, primary_text, q, company=company)
                    score2 = accepted.get("predicted_val")
                    rat2 = (accepted.get("rationale") or "").strip()
                    cite2 = (accepted.get("citation") or "").strip()
                    still = False
                    if score2 is not None and round(float(score2), 2) != 0.0:
                        if rat2 and normalize_text(rat2) in peer_rationale(qid, company):
                            still = True
                        if cite2 and len(normalize_text(cite2)) >= 12 and normalize_text(cite2) in peer_citation(qid, company):
                            still = True
                    if still:
                        accepted = ext._withhold(
                            qid,
                            [{"check": "rationale_generic", "detail": f"{qid} cross-company clone"}],
                            error_code="WITHHELD_UNSUPPORTED_CLAIM",
                        )

                by_qid[qid] = accepted
                company_done += 1
                progress["done"] += 1
            except Exception as exc:
                by_qid[qid] = ext._withhold(
                    qid, [{"check": "timeout", "detail": str(exc)}], error_code="TIMEOUT"
                )
                company_fail += 1
                progress["failed"] += 1

        # Preserve order: original order then any new
        out = []
        seen = set()
        for rec in records:
            qid = str(rec.get("q_id"))
            out.append(by_qid.get(qid, rec))
            seen.add(qid)
        for qid, rec in by_qid.items():
            if qid not in seen:
                out.append(rec)
        tmp = cache / f"{company}.tmp.json"
        tmp.write_text(json.dumps(out, indent=2))
        tmp.replace(cache_file)

        # Refresh primary map from live category contexts
        primary_map = {
            cat: (category_contexts.get(cat) or {}).get("primary_text", "")
            for cat in ext.CAT_PRIMARY_SOURCES
        }
        (cache / f"{company}.primary_map.json").write_text(json.dumps(primary_map))

        progress["companies"][company] = {
            "regen": company_done,
            "failed": company_fail,
            "qids": sorted(qids),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        prog_path.write_text(json.dumps(progress, indent=2))
        print(json.dumps({"company": company, "regen": company_done, "failed": company_fail}))

    progress["finished_at"] = datetime.now(timezone.utc).isoformat()
    prog_path.write_text(json.dumps(progress, indent=2))
    print(json.dumps({"done": progress["done"], "failed": progress["failed"], "progress": str(prog_path)}))
    return 0 if progress["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
