"""Audit parsed-markdown scores: exact quote, rationale claims, no PDF provenance.

Non-zero scores require a citation that is an exact span of the category's
primary markdown. A score of 0.0 may omit a citation. source_pdf and page_number
are ignored.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from src.scorer.schemas import is_scaffolding_citation, match_citation_to_text

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

CLAIM_RE = re.compile(r"\bSDG\s*\d+\b|\$\s?\d[\d,]*|\b\d+(?:\.\d+)?\s*%", re.IGNORECASE)
SDG_QUESTION_RE = re.compile(r"\bSDGs?\b|sustainable development goal", re.IGNORECASE)
# Narrative impact themes (Wave 2): allow ES_Q1-class scores without literal "SDG N"
# when the citation itself carries grounded founder impact language.
IMPACT_NARRATIVE_RE = re.compile(
    r"\b("
    r"climate|carbon|emission|decarbon|renewable|clean\s+energy|greenhouse|"
    r"equity|underserved|community|affordable|waste|circular|recycl|"
    r"water|biodiversity|sustainab|social\s+impact|environmental\s+impact|"
    r"net[\s-]?zero|ghg|pollution|conservation"
    r")\b",
    re.IGNORECASE,
)


def _finding(check: str, detail: str) -> dict[str, str]:
    return {"check": check, "detail": detail}


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


def _is_zero(score: Any) -> bool:
    return score is not None and round(float(score), 2) == 0.0


def audit_parsed_records(
    records: list[dict[str, Any]],
    primary_text_by_cat: dict[str, str],
    rubric: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Check scores and citations against continuous primary markdown per category."""
    findings = []
    questions = _load_questions(rubric)
    for record in records:
        qid = record.get("q_id") or "?"
        question = questions.get(qid)
        cat = (question or {}).get("cat_code") or qid.split("_")[0]
        score = record.get("predicted_val")
        confidence = record.get("confidence")
        citation = record.get("citation")
        rationale = record.get("rationale") or ""
        primary_text = primary_text_by_cat.get(cat) or ""

        if score is not None and round(float(score), 2) not in _allowed_scores(question):
            findings.append(_finding("score_option", f"{qid} score {score} is not an allowed option"))
        if confidence is None or not 0.0 <= float(confidence) <= 1.0:
            findings.append(_finding("confidence", f"{qid} confidence {confidence} is outside 0 to 1"))
        if score is not None and not _is_zero(score) and not citation:
            findings.append(_finding("citation_missing", f"{qid} has a non-zero score and no citation"))
        if score is not None and not rationale.strip():
            findings.append(_finding("rationale_missing", f"{qid} has a score and no rationale"))
        if citation and is_scaffolding_citation(citation):
            findings.append(_finding("citation_template", f"{qid} citation is template text"))
        if citation and not match_citation_to_text(citation, primary_text):
            findings.append(_finding(
                "citation_ungrounded",
                f"{qid} citation is not an exact span of the {cat} primary markdown",
            ))

        source_text = primary_text.lower()
        citation_text = (citation or "").lower()
        for claim in CLAIM_RE.findall(rationale):
            token = claim.lower().replace(" ", "")
            haystack = source_text.replace(" ", "") + " " + citation_text.replace(" ", "")
            if token not in haystack:
                findings.append(_finding(
                    "rationale_unsupported",
                    f"{qid} rationale names {claim!r}, which is not in the primary text",
                ))

        question_text = (question or {}).get("text") or ""
        # Wave 2: non-zero SDG-question scores may rest on grounded narrative impact
        # in the citation. Still require *some* SDG label in primary OR impact
        # narrative in the citation span. Invented SDG N / $ / % stay blocked above.
        if SDG_QUESTION_RE.search(question_text) and score not in (None, 0, 0.0):
            has_sdg_label = (
                "sdg" in source_text or "sustainable development" in source_text
            )
            has_narrative = bool(IMPACT_NARRATIVE_RE.search(citation or ""))
            if not has_sdg_label and not has_narrative:
                findings.append(_finding(
                    "score_without_sdg",
                    f"{qid} scores {score} for an SDG question without SDG labels "
                    f"in primary or impact narrative in the citation",
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
    parser = argparse.ArgumentParser(description="Audit v5 parsed-markdown scores.")
    parser.add_argument("--primary-map", required=True, help="JSON map cat_code -> primary markdown text")
    parser.add_argument("--extraction", required=True)
    parser.add_argument("--rubric", default="master_282_rubric.json")
    args = parser.parse_args(argv)

    primary_text_by_cat = json.loads(Path(args.primary_map).read_text())
    records = load_records(json.loads(Path(args.extraction).read_text()))
    rubric_path = Path(args.rubric)
    rubric = json.loads(rubric_path.read_text()) if rubric_path.is_file() else None

    findings = audit_parsed_records(records, primary_text_by_cat, rubric)
    print(f"records {len(records)} categories {len(primary_text_by_cat)}")
    for cat in CAT_PRIMARY_SOURCES:
        text = primary_text_by_cat.get(cat) or ""
        print(f"  {cat}: {len(text)} chars")
    if not findings:
        print("PASS")
        return 0
    for finding in findings:
        print(f"FAIL {finding['check']}: {finding['detail']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
