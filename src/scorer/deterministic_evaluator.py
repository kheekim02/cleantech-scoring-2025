# src/scorer/deterministic_evaluator.py
from __future__ import annotations
import re

PATENT_RE = re.compile(
    r"\b(?:US|EP|WO)\s?\d{7,8}[A-Z\d]?\b|\bpatent(?:\s+(?:number|no\.?|#|issued|application))?\s*(?:US|EP|WO)?\s*\d{6,8}\b|\bissued\s+patents?\b",
    re.IGNORECASE,
)

BREAKEVEN_RE = re.compile(
    r"\b(?:break[\s-]?even\s+(?:in|by|reached|achieved|at)\s+(?:year|month|\d{4})|cash\s+flow\s+positive\s+(?:in|by)\s+year\s*\d|breakeven\s+in\s+year\s*\d)\b",
    re.IGNORECASE,
)

CORP_ENTITY_RE = re.compile(
    r"\b(?:delaware\s+c[\s-]?corp|c[\s-]?corporation|incorporated\s+in\s+delaware|delaware\s+llc|limited\s+liability\s+company)\b",
    re.IGNORECASE,
)

PROJECTIONS_3YR_RE = re.compile(
    r"\b(?:3[\s-]year\s+(?:financial\s+)?projections?"
    r"|year\s*1\b[^\n]{0,200}?year\s*2\b[^\n]{0,200}?year\s*3\b"
    r"|\by1\b[^\n]{0,120}?\by2\b[^\n]{0,120}?\by3\b)",
    re.IGNORECASE,
)

DETERMINISTIC_RULES = {
    "F_Q1": {"pattern": PROJECTIONS_3YR_RE, "label": "3-Year financial projection model detected"},
    "F_Q7": {"pattern": BREAKEVEN_RE, "label": "Breakeven detected in financial projections"},
    "L_Q1": {"pattern": CORP_ENTITY_RE, "label": "Corporate legal entity structure verified"},
    "L_Q14": {"pattern": PATENT_RE, "label": "Issued patent detected in legal deliverables"},
}


def find_deterministic_evidence(q_id: str, primary_text: str | None) -> str | None:
    """Return the verbatim source line that satisfies a deterministic rule, else None."""
    if not primary_text or q_id not in DETERMINISTIC_RULES:
        return None
    match = DETERMINISTIC_RULES[q_id]["pattern"].search(primary_text)
    if not match:
        return None
    line_start = primary_text.rfind("\n", 0, match.start()) + 1
    line_end = primary_text.find("\n", match.end())
    if line_end == -1:
        line_end = len(primary_text)
    line = primary_text[line_start:line_end].strip()
    return line or None


def evaluate_deterministic_criterion(
    q_id: str,
    raw_text: str | None,
    current_val: float | None,
) -> tuple[float | None, bool, str]:
    """Overrides subjective/flawed LLM evaluation with deterministic regex checks on primary markdown."""
    if not raw_text or q_id not in DETERMINISTIC_RULES:
        return current_val, False, ""

    rule = DETERMINISTIC_RULES[q_id]
    match = rule["pattern"].search(raw_text)
    if match:
        snippet = match.group(0).replace("\n", " ").strip()
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        return 1.0, True, f"Deterministic Override: {rule['label']} ('{snippet}')."

    return current_val, False, ""
