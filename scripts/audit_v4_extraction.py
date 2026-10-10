"""Audit Docling chunks and model scores against the founder text.

A citation must land in a primary chunk for its category. A rationale may not
name an SDG, dollar amount, or percentage that the primary text does not contain.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from scripts.docling_ingestion import DOC_TYPE_INTERFACE, resolve_doc_type
from src.scorer.schemas import is_scaffolding_citation, match_citation_to_chunks

CAT_PRIMARY_SOURCES = {
    "BC": ["EBD1"],
    "ES": ["EBD2", "M2"],
    "F": ["EBD5", "M6"],
    "IP": ["EBD8"],
    "IS": ["EBD6"],
    "L": ["M7"],
    "M": ["EBD3", "M4"],
    "PMF": ["M3", "M1"],
    "T": ["M8"],
    "TP": ["EBD4"],
}

TEMPLATE_MARKERS = (
    "essential business deliverable",
    "upload this document as",
    "do not duplicate",
    "instructions:",
)
CLAIM_RE = re.compile(r"\bSDG\s*\d+\b|\$\s?\d[\d,]*|\b\d+(?:\.\d+)?\s*%", re.IGNORECASE)
SDG_QUESTION_RE = re.compile(r"\bSDGs?\b|sustainable development goal", re.IGNORECASE)


def _finding(check: str, detail: str) -> dict[str, str]:
    return {"check": check, "detail": detail}


def audit_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Check chunk shape, template leakage, and filename-versus-opening type."""
    findings = []
    by_file: dict[str, list[dict[str, Any]]] = {}
    for index, chunk in enumerate(chunks):
        name = chunk.get("source_pdf") or f"chunk[{index}]"
        missing = [key for key in ("source_pdf", "doc_type", "page_no", "text") if chunk.get(key) in (None, "")]
        if missing:
            findings.append(_finding("chunk_fields", f"{name} missing {', '.join(missing)}"))
            continue
        if not isinstance(chunk.get("page_no"), int) or chunk["page_no"] < 1:
            findings.append(_finding("chunk_page", f"{name} page_no={chunk.get('page_no')}"))
        lowered = chunk["text"].lower()
        for marker in TEMPLATE_MARKERS:
            if marker in lowered:
                findings.append(_finding("chunk_template", f"{name} p.{chunk['page_no']} contains {marker!r}"))
                break
        by_file.setdefault(chunk["source_pdf"], []).append(chunk)

    for filename, file_chunks in by_file.items():
        opening = "\n".join(chunk["text"] for chunk in file_chunks)[:1200]
        resolved = resolve_doc_type(filename, opening)
        stamped = file_chunks[0].get("doc_type")
        if DOC_TYPE_INTERFACE.get(resolved) != DOC_TYPE_INTERFACE.get(stamped) and resolved != stamped:
            findings.append(_finding(
                "chunk_doc_type",
                f"{filename} stamped {stamped}, opening resolves to {resolved}",
            ))
    return findings


def category_coverage(chunks: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Primary filenames present for each scoring category."""
    present = {chunk.get("doc_type") for chunk in chunks}
    covered = {}
    for cat, types in CAT_PRIMARY_SOURCES.items():
        names = sorted({
            chunk["source_pdf"]
            for chunk in chunks
            if chunk.get("doc_type") in types and chunk.get("source_pdf")
        })
        covered[cat] = names
        if not names and not any(doc_type in present for doc_type in types):
            covered[cat] = []
    return covered


def _primary_text(chunks: list[dict[str, Any]], doc_types: set[str]) -> str:
    return "\n".join(
        chunk.get("text") or ""
        for chunk in chunks
        if chunk.get("doc_type") in doc_types
    )


def _allowed_scores(question: dict[str, Any] | None) -> set[float]:
    if question:
        vals = []
        for option in question.get("options") or []:
            raw = option.get("val") if isinstance(option, dict) else option
            if raw is not None:
                vals.append(round(float(raw), 2))
        if vals:
            return set(vals)
    return {0.0, 0.25, 0.5, 0.75, 1.0}


def _load_questions(rubric: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    questions = {}
    for question in rubric or []:
        qid = question.get("new_q_id") or question.get("q_id")
        if qid:
            questions[qid] = question
    return questions


def audit_records(
    records: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    rubric: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Check each score, its citation, and its rationale against primary chunks."""
    findings = []
    questions = _load_questions(rubric)
    for record in records:
        qid = record.get("q_id") or "?"
        question = questions.get(qid)
        cat = (question or {}).get("cat_code") or qid.split("_")[0]
        primary_types = set(CAT_PRIMARY_SOURCES.get(cat, []))
        score = record.get("predicted_val")
        confidence = record.get("confidence")
        citation = record.get("citation")
        rationale = record.get("rationale") or ""

        if score is not None and round(float(score), 2) not in _allowed_scores(question):
            findings.append(_finding("score_option", f"{qid} score {score} is not an allowed option"))
        if confidence is None or not 0.0 <= float(confidence) <= 1.0:
            findings.append(_finding("confidence", f"{qid} confidence {confidence} is outside 0 to 1"))
        if score is not None and not citation:
            findings.append(_finding("citation_missing", f"{qid} has a score and no citation"))
        if score is not None and not rationale.strip():
            findings.append(_finding("rationale_missing", f"{qid} has a score and no rationale"))
        if citation and is_scaffolding_citation(citation):
            findings.append(_finding("citation_template", f"{qid} citation is template text"))

        primary_chunks = [c for c in chunks if c.get("doc_type") in primary_types]
        search_chunks = primary_chunks or chunks
        matched = match_citation_to_chunks(citation, search_chunks) if citation else None
        if citation and matched is None:
            anywhere = match_citation_to_chunks(citation, chunks)
            if anywhere is None:
                findings.append(_finding("citation_ungrounded", f"{qid} citation is not in any chunk"))
            elif primary_types:
                source = anywhere.get("source_pdf")
                stamped = next((c.get("doc_type") for c in chunks if c.get("source_pdf") == source), None)
                findings.append(_finding(
                    "citation_not_primary",
                    f"{qid} citation is in {source} ({stamped}), not a {cat} primary",
                ))

        source_text = _primary_text(chunks, primary_types).lower()
        citation_text = (citation or "").lower()
        for claim in CLAIM_RE.findall(rationale):
            token = claim.lower().replace(" ", "")
            haystack = source_text.replace(" ", "") + " " + citation_text.replace(" ", "")
            if token not in haystack:
                findings.append(_finding("rationale_unsupported", f"{qid} rationale names {claim!r}, which is not in the primary text"))

        question_text = (question or {}).get("text") or ""
        if SDG_QUESTION_RE.search(question_text) and score not in (None, 0, 0.0):
            if "sdg" not in source_text and "sustainable development" not in source_text:
                findings.append(_finding(
                    "score_without_sdg",
                    f"{qid} scores {score} for an SDG question, and the primary text does not name an SDG",
                ))
    return findings


def load_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return [payload["result"]]
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    raise ValueError("extraction file must be a list of records or a smoke result with 'result'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit v4 chunks and extracted scores.")
    parser.add_argument("--chunks", required=True)
    parser.add_argument("--extraction", required=True)
    parser.add_argument("--rubric", default="master_282_rubric.json")
    args = parser.parse_args(argv)

    chunks = json.loads(Path(args.chunks).read_text())
    records = load_records(json.loads(Path(args.extraction).read_text()))
    rubric_path = Path(args.rubric)
    rubric = json.loads(rubric_path.read_text()) if rubric_path.is_file() else None

    chunk_findings = audit_chunks(chunks)
    record_findings = audit_records(records, chunks, rubric)
    coverage = category_coverage(chunks)
    print(f"chunks {len(chunks)} records {len(records)}")
    for cat, names in coverage.items():
        print(f"  {cat}: {', '.join(names) if names else 'none'}")
    findings = chunk_findings + record_findings
    if not findings:
        print("PASS")
        return 0
    for finding in findings:
        print(f"FAIL {finding['check']}: {finding['detail']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
