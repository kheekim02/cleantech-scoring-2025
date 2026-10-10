"""Short withheld-citation audit for the five-company expansion sample.

Saved shadow records null the citation after a withhold, so this script re-asks
the model, keeps the raw quote, and classifies why the exact-span gate rejected it.
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
    match_citation_to_chunks,
    normalize_text,
)


def load_extractor(path: Path):
    spec = importlib.util.spec_from_file_location("extractor_v2_withheld", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def token_set(text: str) -> set[str]:
    return set(normalize_text(text).split())


def best_overlap(citation: str, chunks: list[dict[str, Any]]) -> tuple[float, dict[str, Any] | None]:
    cite_tokens = token_set(citation)
    if not cite_tokens:
        return 0.0, None
    best = 0.0
    best_chunk = None
    for chunk in chunks:
        chunk_tokens = token_set(chunk.get("text") or "")
        if not chunk_tokens:
            continue
        overlap = len(cite_tokens & chunk_tokens) / len(cite_tokens)
        if overlap > best:
            best = overlap
            best_chunk = chunk
    return best, best_chunk


def longest_common_word_run(citation: str, chunk_text: str) -> int:
    a = normalize_text(citation).split()
    b = normalize_text(chunk_text).split()
    if not a or not b:
        return 0
    best = 0
    b_index = {word: [] for word in set(b)}
    for i, word in enumerate(b):
        b_index.setdefault(word, []).append(i)
    for i, word in enumerate(a):
        for j in b_index.get(word, []):
            length = 0
            while i + length < len(a) and j + length < len(b) and a[i + length] == b[j + length]:
                length += 1
            if length > best:
                best = length
    return best


def classify_citation(
    citation: str | None,
    predicted_val: Any,
    chunks: list[dict[str, Any]],
    primary_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    if predicted_val is None and not citation:
        return {"class": "model_null", "detail": "model returned no score and no citation"}
    if not citation or not str(citation).strip():
        return {"class": "empty_citation", "detail": "model scored without a citation"}
    if is_negative_citation(citation):
        return {"class": "negative_citation", "detail": "citation is a statement of absence"}
    if is_scaffolding_citation(citation):
        return {"class": "scaffolding", "detail": "citation matches template language"}

    words = normalize_text(citation).split()
    primary_hit = match_citation_to_chunks(citation, primary_chunks)
    if primary_hit:
        return {
            "class": "would_pass",
            "detail": "exact primary span",
            "source_pdf": primary_hit.get("source_pdf"),
            "page_number": primary_hit.get("page_number"),
        }

    anywhere = match_citation_to_chunks(citation, chunks)
    if anywhere:
        return {
            "class": "wrong_document",
            "detail": "exact span exists only outside the category primary set",
            "source_pdf": anywhere.get("source_pdf"),
            "page_number": anywhere.get("page_number"),
        }

    if 4 <= len(words) <= 7:
        overlap, chunk = best_overlap(citation, primary_chunks)
        if overlap >= 0.99 and chunk is not None:
            return {
                "class": "medium_length_policy",
                "detail": "4-7 word exact token span rejected by policy",
                "source_pdf": chunk.get("source_pdf"),
                "page_number": chunk.get("page_no"),
            }

    # Splice heuristic: separate sentences each land in some chunk, but not as one span.
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", citation) if part.strip()]
    if len(sentences) >= 2:
        hits = []
        for sentence in sentences:
            hit = match_citation_to_chunks(sentence, primary_chunks) or match_citation_to_chunks(sentence, chunks)
            hits.append(hit)
        if all(hits):
            ids = {(hit.get("source_pdf"), hit.get("chunk_id"), hit.get("page_number")) for hit in hits}
            if len(ids) > 1:
                return {
                    "class": "splice",
                    "detail": "sentences match different chunks",
                    "sources": [
                        {"source_pdf": hit.get("source_pdf"), "page_number": hit.get("page_number")}
                        for hit in hits
                    ],
                }

    if len(words) >= 10:
        mid = len(words) // 2
        left = " ".join(words[:mid])
        right = " ".join(words[mid:])
        left_hit = match_citation_to_chunks(left, primary_chunks) or match_citation_to_chunks(left, chunks)
        right_hit = match_citation_to_chunks(right, primary_chunks) or match_citation_to_chunks(right, chunks)
        if left_hit and right_hit:
            same = (
                left_hit.get("chunk_id") == right_hit.get("chunk_id")
                and left_hit.get("source_pdf") == right_hit.get("source_pdf")
            )
            if not same:
                return {
                    "class": "splice",
                    "detail": "halves match different chunks",
                    "left_pdf": left_hit.get("source_pdf"),
                    "right_pdf": right_hit.get("source_pdf"),
                }

    overlap, chunk = best_overlap(citation, primary_chunks or chunks)
    run = longest_common_word_run(citation, (chunk or {}).get("text") or "") if chunk else 0
    if overlap >= 0.6 and run >= 5:
        return {
            "class": "paraphrase_or_edit",
            "detail": f"token overlap {overlap:.2f}, longest exact word run {run}",
            "source_pdf": (chunk or {}).get("source_pdf"),
            "page_number": (chunk or {}).get("page_no"),
            "chunk_excerpt": ((chunk or {}).get("text") or "")[:240],
        }
    if overlap >= 0.35:
        return {
            "class": "weak_paraphrase",
            "detail": f"token overlap {overlap:.2f}, longest exact word run {run}",
            "source_pdf": (chunk or {}).get("source_pdf"),
            "page_number": (chunk or {}).get("page_no"),
            "chunk_excerpt": ((chunk or {}).get("text") or "")[:240],
        }
    return {
        "class": "fabricated",
        "detail": f"token overlap {overlap:.2f}, longest exact word run {run}",
        "source_pdf": (chunk or {}).get("source_pdf"),
        "page_number": (chunk or {}).get("page_no"),
    }


def select_targets(cache_dir: Path, seed: int = 2026) -> list[dict[str, str]]:
    """All BC citation-withholds plus a fixed IP sample and a few cross-category cases."""
    rng = random.Random(seed)
    targets: list[dict[str, str]] = []
    ip_pool: list[dict[str, str]] = []
    other_pool: list[dict[str, str]] = []
    rationale_pool: list[dict[str, str]] = []

    for path in sorted(cache_dir.glob("*.json")):
        company = path.stem
        for row in json.loads(path.read_text()):
            if row.get("predicted_val") is not None:
                continue
            rationale = row.get("rationale") or ""
            qid = row["q_id"]
            cat = qid.split("_")[0]
            item = {"startup_id": company, "q_id": qid, "saved_rationale": rationale}
            if "rationale introduced a figure" in rationale:
                rationale_pool.append(item)
                continue
            if "exact continuous span" not in rationale:
                continue
            if cat == "BC":
                targets.append(item)
            elif cat == "IP":
                ip_pool.append(item)
            else:
                other_pool.append(item)

    targets.extend(rng.sample(ip_pool, min(25, len(ip_pool))))
    targets.extend(rng.sample(other_pool, min(10, len(other_pool))))
    targets.extend(rationale_pool[:5])
    # Stable unique order
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
    parser = argparse.ArgumentParser(description="Re-query withheld answers and classify raw citations.")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--chunks-dir", required=True)
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

    for index, item in enumerate(targets, 1):
        startup_id = item["startup_id"]
        qid = item["q_id"]
        question = rubric[qid]
        cat = question.get("cat_code") or qid.split("_")[0]
        chunks = json.loads((Path(args.chunks_dir) / startup_id / "chunks.json").read_text())
        doc_manifest = extractor.build_doc_manifest(chunks)
        ctx = extractor.build_category_context(chunks, cat)
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
        primary = extractor._primary_chunks(chunks, cat)
        classification = classify_citation(
            raw.get("citation"),
            raw.get("predicted_val"),
            chunks,
            primary,
        )
        gated = extractor.accept_model_answer(raw, chunks, question)
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
            "classification_meta": {
                k: v for k, v in classification.items() if k not in {"class", "detail"}
            },
            "gate_predicted_val": gated.get("predicted_val"),
            "gate_rationale": gated.get("rationale"),
            "primary_chars": len(ctx["text"]),
            "primary_files": ctx["primary_filenames"],
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
        "selection": "all BC citation-withholds + 25 IP + 10 other citation-withholds + up to 5 rationale-figure",
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
