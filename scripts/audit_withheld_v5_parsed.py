"""Short withheld audit for parsed-markdown (v5) scores.

Re-asks withheld questions against continuous primary markdown, keeps the raw
quote, and classifies why the gate rejected it. No Docling / page provenance.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scorer.schemas import (  # noqa: E402
    is_negative_citation,
    is_scaffolding_citation,
    match_citation_to_text,
    normalize_text,
)


def load_extractor(path: Path):
    spec = importlib.util.spec_from_file_location("extractor_v5_withheld", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def token_set(text: str) -> set[str]:
    return set(normalize_text(text).split())


def best_overlap(citation: str, text: str) -> tuple[float, int]:
    cite_tokens = normalize_text(citation).split()
    body_tokens = normalize_text(text).split()
    if not cite_tokens or not body_tokens:
        return 0.0, 0
    cite_set = set(cite_tokens)
    body_set = set(body_tokens)
    overlap = len(cite_set & body_set) / len(cite_set)
    # longest common contiguous word run
    best = 0
    index = {w: [] for w in set(body_tokens)}
    for i, w in enumerate(body_tokens):
        index.setdefault(w, []).append(i)
    for i, w in enumerate(cite_tokens):
        for j in index.get(w, []):
            length = 0
            while (
                i + length < len(cite_tokens)
                and j + length < len(body_tokens)
                and cite_tokens[i + length] == body_tokens[j + length]
            ):
                length += 1
            if length > best:
                best = length
    return overlap, best


def classify_against_primary(
    citation: str | None,
    predicted_val: Any,
    primary_text: str,
) -> dict[str, Any]:
    if predicted_val is None and not citation:
        return {"class": "model_null", "detail": "model returned no score and no citation"}
    if not citation or not str(citation).strip():
        if predicted_val is not None and round(float(predicted_val), 2) == 0.0:
            return {"class": "zero_without_citation", "detail": "zero score with no quote (should keep)"}
        return {"class": "empty_citation", "detail": "model scored without a citation"}
    if is_negative_citation(citation):
        return {"class": "negative_citation", "detail": "citation is a statement of absence"}
    if is_scaffolding_citation(citation):
        return {"class": "scaffolding", "detail": "citation matches template language"}
    if match_citation_to_text(citation, primary_text):
        return {"class": "would_pass", "detail": "exact span of primary markdown"}

    overlap, run = best_overlap(citation, primary_text)
    if overlap >= 0.6 and run >= 5:
        return {
            "class": "paraphrase_or_edit",
            "detail": f"token overlap {overlap:.2f}, longest exact word run {run}",
        }
    if overlap >= 0.35:
        return {
            "class": "weak_paraphrase",
            "detail": f"token overlap {overlap:.2f}, longest exact word run {run}",
        }
    return {
        "class": "fabricated",
        "detail": f"token overlap {overlap:.2f}, longest exact word run {run}",
    }


def select_targets(cache_dir: Path, seed: int = 2026) -> list[dict[str, str]]:
    """Stratified sample of all withheld answers, biased to heavy categories."""
    rng = random.Random(seed)
    by_cat: dict[str, list[dict[str, str]]] = {}
    rationale_pool: list[dict[str, str]] = []

    for path in sorted(cache_dir.glob("*.json")):
        if path.name.endswith(".primary_map.json"):
            continue
        company = path.stem
        for row in json.loads(path.read_text()):
            if row.get("predicted_val") is not None:
                continue
            rationale = row.get("rationale") or ""
            qid = row["q_id"]
            cat = qid.split("_")[0]
            item = {"startup_id": company, "q_id": qid, "saved_rationale": rationale, "cat": cat}
            if "rationale introduced a figure" in rationale:
                rationale_pool.append(item)
            by_cat.setdefault(cat, []).append(item)

    targets: list[dict[str, str]] = []
    # Take all withholds from small categories; sample larger ones.
    for cat, pool in sorted(by_cat.items()):
        if cat in {"IP", "PMF", "IS", "T", "F", "L"} and len(pool) > 12:
            targets.extend(rng.sample(pool, 12))
        else:
            targets.extend(pool)
    targets.extend(rationale_pool[:8])

    seen = set()
    ordered = []
    for item in targets:
        key = (item["startup_id"], item["q_id"])
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-query v5 withheld answers against parsed markdown.")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--parsed-dir", required=True)
    parser.add_argument("--rubric", required=True)
    parser.add_argument("--extractor", default=str(ROOT / "scripts" / "14_ai_copilot_extractor_v2.py"))
    parser.add_argument("--endpoint", default="http://127.0.0.1:11435/v1")
    parser.add_argument("--model", default="qwen3.8:27b-32k")
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    extractor = load_extractor(Path(args.extractor))
    rubric = {
        q.get("new_q_id") or q.get("q_id"): q
        for q in json.loads(Path(args.rubric).read_text())
    }
    targets = select_targets(Path(args.cache_dir), seed=args.seed)
    if args.limit:
        targets = targets[: args.limit]

    results = []
    classes = Counter()
    by_cat = Counter()
    docs_cache: dict[str, list[dict[str, Any]]] = {}

    for index, item in enumerate(targets, 1):
        startup_id = item["startup_id"]
        qid = item["q_id"]
        question = rubric[qid]
        cat = question.get("cat_code") or qid.split("_")[0]
        if startup_id not in docs_cache:
            docs_cache[startup_id] = extractor.load_parsed_documents(
                Path(args.parsed_dir) / startup_id
            )
        docs = docs_cache[startup_id]
        doc_manifest = extractor.build_doc_manifest_from_docs(docs)
        ctx = extractor.build_category_context_from_docs(docs, cat)
        raw = extractor.query_sglang_question(
            None,
            args.model,
            ctx["text"],
            question,
            180,
            doc_manifest,
            ctx["has_primary"],
            args.endpoint,
        )
        primary_text = ctx.get("primary_text") or ""
        classification = classify_against_primary(
            raw.get("citation"),
            raw.get("predicted_val"),
            primary_text,
        )
        gated = extractor.accept_model_answer(raw, primary_text, question)
        row = {
            "startup_id": startup_id,
            "q_id": qid,
            "cat_code": cat,
            "saved_rationale": item["saved_rationale"],
            "raw_predicted_val": raw.get("predicted_val"),
            "raw_confidence": raw.get("confidence"),
            "raw_citation": raw.get("citation"),
            "raw_rationale": raw.get("rationale"),
            "classification": classification["class"],
            "classification_detail": classification.get("detail"),
            "gate_predicted_val": gated.get("predicted_val"),
            "gate_rationale": gated.get("rationale"),
            "primary_chars": len(primary_text),
            "primary_files": ctx.get("primary_filenames"),
        }
        results.append(row)
        classes[classification["class"]] += 1
        by_cat[f"{cat}:{classification['class']}"] += 1
        print(
            f"[{index}/{len(targets)}] {startup_id} {qid} -> {classification['class']} "
            f"| raw_score={raw.get('predicted_val')} gate={gated.get('predicted_val')}",
            flush=True,
        )

    summary = {
        "sample_size": len(results),
        "seed": args.seed,
        "selection": "stratified withholds from ai_cache_v5_parsed against parsed_clean_v4",
        "class_counts": dict(classes.most_common()),
        "class_by_category": dict(sorted(by_cat.items())),
        "results": results,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print("WROTE", out)
    print("CLASS_COUNTS", json.dumps(summary["class_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
