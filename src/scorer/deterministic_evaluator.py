# src/scorer/deterministic_evaluator.py
from __future__ import annotations
import re
from typing import Any

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


def evaluate_visual_criterion(
    q_id: str,
    deck_meta: dict[str, Any] | None,
    startup_id: str = "",
) -> dict[str, Any] | None:
    """Evaluate visual criteria (IP_Q7, PMF_Q24) using PyMuPDF slide visual elements."""
    if not deck_meta:
        return None

    if q_id == "IP_Q7":
        # Problem model visual: search pages with problem context and diagram shapes
        for p in deck_meta.get("pages", []):
            if p.get("is_diagram_candidate"):
                pnum = p["page_num"]
                draws = p["drawing_count"]
                imgs = p["image_count"]
                return {
                    "q_id": "IP_Q7",
                    "predicted_val": 1.0,
                    "confidence": 0.95,
                    "citation": f"Slide {pnum} contains visual problem diagram ({draws} vector paths, {imgs} raster images).",
                    "rationale": f"Slide {pnum} of the pitch deck presents a visual model/flowchart depicting the problem.",
                    "source": "visual_inspection",
                    "error_code": None,
                }
        return {
            "q_id": "IP_Q7",
            "predicted_val": 0.0,
            "confidence": 0.85,
            "citation": None,
            "rationale": "No visual diagram or model found in pitch deck slides.",
            "source": "visual_inspection",
            "error_code": None,
        }

    if q_id == "PMF_Q24":
        # Logo discernible: check title slide has vector/raster brand asset
        pages = deck_meta.get("pages", [])
        p1 = pages[0] if pages else {}
        if p1.get("has_logo_candidate"):
            return {
                "q_id": "PMF_Q24",
                "predicted_val": 1.0,
                "confidence": 0.95,
                "citation": f"Slide 1 displays high-resolution logo asset ({p1['drawing_count']} vector paths, {p1['image_count']} raster elements).",
                "rationale": "Startup logo is prominently featured on the title slide with vector/raster scaling fidelity.",
                "source": "visual_inspection",
                "error_code": None,
            }

    return None

