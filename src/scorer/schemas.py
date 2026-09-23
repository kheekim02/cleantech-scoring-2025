"""Pydantic v2 schemas and verbatim grounding validators for Diligence Engine."""
from __future__ import annotations
import re
from typing import Any
from pydantic import BaseModel, Field, field_validator

NEGATIVE_CITATION_PATTERNS = [
    r'does not contain',
    r'does not mention',
    r'no mention',
    r'no information',
    r'not provided',
    r'not explicitly mentioned',
    r'there is no',
    r'neither.*is mentioned',
    r'insufficient data',
    r'not found in the document',
    r'no direct evidence',
]

SCAFFOLDING_CITATION_PATTERNS = [
    r'(?i)for\s+the\s+financial\s+projection\s+model',
    r'(?i)use\s+your\s+work\s+in\s+module\s*\d+',
    r'(?i)use\s+your\s+customer\s+acquisition\s+cost',
    r'(?i)three\s+year\s+financial\s+projection:',
    r'(?i)previous\s+assignment\s+sheets',
    r'(?i)validated\s+targeted\s+subsegment',
    r'(?i)loose\s+example',
    r'(?i)blair\s+smith',
    r'(?i)cleantech\s+open',
    r'(?i)character\s+limit',
    r'(?i)do\s+not\s+duplicate',
    r'(?i)answer\s+the\s+questions\s+below',
    r'(?i)upload\s+this\s+document',
    r'(?i)module\s*\d+:\s*[^\n]+assignment',
    r'(?i)building\s+and\s+exporting\s+your\s+model',
    r'(?i)to\s+create\s+a\s+single\s+pdf',
    r'(?i)mac:\s*[\u2018\']print[\u2019\']',
    r'(?i)essential\s+business\s+deliverable',
    r'(?i)make\s+sure\s+your\s+assumptions\s+are\s+credibly\s+based',
]


def normalize_text(s: str | None) -> str:
    """Normalize text for invariant fuzzy matching (lowercase, stripped punctuation, normalized whitespace)."""
    if not s:
        return ""
    # Strip bullet points and common non-breaking chars
    s = re.sub(r'[•●○\u200b\xa0\r\n\t]+', ' ', s)
    # Retain alphanumeric
    s = re.sub(r'[^a-zA-Z0-9]+', ' ', s)
    return ' '.join(s.lower().split())


def is_negative_citation(text: str | None) -> bool:
    """Check if the citation text represents a statement of absence rather than founder evidence."""
    if not text:
        return True
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in NEGATIVE_CITATION_PATTERNS)


def is_scaffolding_citation(text: str | None) -> bool:
    """Check if the citation text contains competition template instructions or guide prompts."""
    if not text:
        return False
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in SCAFFOLDING_CITATION_PATTERNS)


def match_citation_to_chunks(
    citation: str | None,
    chunks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Multi-tier exact/prefix matching of a citation against Docling element chunks.

    Returns the matching chunk metadata (source_pdf, page_number) or None if ungrounded.
    """
    if not citation or len(citation.strip()) < 8:
        return None

    if is_negative_citation(citation) or is_scaffolding_citation(citation):
        return None

    clean_cit = normalize_text(citation)
    words = clean_cit.split()
    if not words:
        return None

    prefix_8 = ' '.join(words[:8]) if len(words) >= 8 else clean_cit
    prefix_5 = ' '.join(words[:5]) if len(words) >= 5 else clean_cit

    # Pre-normalize chunk texts
    chunk_norms = [(c, normalize_text(c.get('text', ''))) for c in chunks]

    # Tier 1: exact normalized match
    for chunk, norm in chunk_norms:
        if clean_cit in norm:
            return {
                "source_pdf": chunk.get("source_pdf"),
                "page_number": chunk.get("page_no"),
                "chunk_id": chunk.get("chunk_id"),
                "match_tier": 1,
            }

    # Tier 2: 8-word prefix match
    if len(words) >= 8:
        for chunk, norm in chunk_norms:
            if prefix_8 in norm:
                return {
                    "source_pdf": chunk.get("source_pdf"),
                    "page_number": chunk.get("page_no"),
                    "chunk_id": chunk.get("chunk_id"),
                    "match_tier": 2,
                }

    # Tier 3: 5-word prefix match (min 15 chars)
    if len(prefix_5) >= 15:
        for chunk, norm in chunk_norms:
            if prefix_5 in norm:
                return {
                    "source_pdf": chunk.get("source_pdf"),
                    "page_number": chunk.get("page_no"),
                    "chunk_id": chunk.get("chunk_id"),
                    "match_tier": 3,
                }

    # Tier 4: Quoted substrings within citation
    quoted = re.findall(r'[\'"]([^\'"]{10,})[\'"]', citation)
    for subq in quoted:
        clean_sub = normalize_text(subq)
        if len(clean_sub) >= 10:
            for chunk, norm in chunk_norms:
                if clean_sub in norm:
                    return {
                        "source_pdf": chunk.get("source_pdf"),
                        "page_number": chunk.get("page_no"),
                        "chunk_id": chunk.get("chunk_id"),
                        "match_tier": 4,
                    }

    return None


class QuestionEvaluation(BaseModel):
    """Schema for individual rubric question evaluation."""
    q_id: str
    predicted_val: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    citation: str | None = None
    source_pdf: str | None = None
    page_number: int | None = None
    rationale: str | None = None

    @field_validator("citation")
    @classmethod
    def sanitize_citation(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        v_clean = v.strip()
        if len(v_clean) < 10 or is_negative_citation(v_clean) or is_scaffolding_citation(v_clean):
            return None
        return v_clean


class RawModelExtraction(BaseModel):
    """Instructor-compatible structured output for LLM generation."""
    q_id: str = Field(description="Rubric Question ID, e.g. BC_Q1, ES_Q3")
    predicted_val: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Assigned score on standardized scale (0.0, 0.25, 0.5, 0.75, 1.0) or null if unanswerable"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    citation: str | None = Field(
        default=None,
        description="Exact verbatim quote of 1-2 complete sentences from applicant text, or null if no evidence"
    )
    rationale: str | None = Field(
        default=None,
        description="Brief 1-sentence justification of the verdict"
    )

    @field_validator("citation")
    @classmethod
    def sanitize_citation(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        v_clean = v.strip()
        if len(v_clean) < 10 or is_negative_citation(v_clean) or is_scaffolding_citation(v_clean):
            return None
        return v_clean

