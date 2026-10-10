"""Pydantic v2 schemas and verbatim grounding validators for Diligence Engine."""
from __future__ import annotations
import re
from typing import Any
from pydantic import BaseModel, Field, field_validator

NEGATIVE_CITATION_PATTERNS = [
    # Evaluator / model language about missing evidence — not founder market-gap prose.
    r'(?:document|text|provided|packet|materials?|applicant)\s+(?:does|do)\s+not\s+(?:contain|mention|include)',
    r'(?:does|do)\s+not\s+mention',
    r'(?:there\s+is\s+)?no\s+(?:mention|information|evidence|discussion|data)\s+(?:of|regarding|about|on)',
    r'not\s+explicitly\s+mentioned',
    r'not\s+provided',
    r'insufficient\s+data',
    r'not\s+found\s+in\s+the\s+document',
    r'no\s+direct\s+evidence',
    r'neither\s+.*\s+is\s+mentioned',
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
    # Residual Cleantech Open worksheet stubs that survived prior cleans
    r'(?i)less\s+taxation',
    r'(?i)interview\s+sampling',
    r'(?i)customer\s+interview\s+(?:guide|script|template)',
    r'(?i)sample\s+interview\s+questions',
    r'(?i)assignment\s+worksheet',
    r'(?i)financial\s+model\s+template',
    # Wave-1 template prompt leaks accepted as citations
    r'(?i)document\s+a\s+sampling.*?customer\s+interviews',
    r'(?i)sampling\s*\(below\)\s*of\s+at\s+least\s+\d+\s+customer',
    r'(?i)markets:\s*describe\s+the\s+size\s+and\s+growth\s+rate',
    r'(?i)size\s+the\s+second\s+and\s+third\s+markets',
    r'(?i)use\s+of\s+funds:\s*specific\s+product',
    r'(?i)describe\s+the\s+size\s+and\s+growth\s+rate\s+of\s+your\s+first\s+targeted',
]

# Pipeline-written rationales that must never be treated as founder diligence prose.
ENGINEERED_RATIONALE_PHRASES = (
    "score based on the cited primary text only",
    "evaluation failed or timed out",
    "no primary source document was classified for this category",
    "no primary source document",
    "score withheld:",
)

# Non-entity micro-stubs that must not satisfy short-cite exemptions on non-zero scores.
JUNK_MICRO_CITATION_NORMS = frozenset({
    "na", "n a", "n/a", "no", "yes", "none", "null", "nil", "tbd", "tba",
    "unknown", "n/a.", "diagram", "value propositions", "key activities",
    "key resources", "customer segments", "channels", "revenue streams",
    "cost structure", "customer relationships",
})

ERROR_CODES = (
    "TIMEOUT",
    "NO_PRIMARY",
    "NO_EVIDENCE",
    "WITHHELD_UNGROUNDED",
    "WITHHELD_UNSUPPORTED_CLAIM",
    "WITHHELD_SCORE_ABSENCE_MISMATCH",
)


def normalize_text(s: str | None) -> str:
    """Normalize text for invariant fuzzy matching (lowercase, stripped punctuation, normalized whitespace)."""
    if not s:
        return ""
    # Strip bullet points and common non-breaking chars
    s = re.sub(r'[•●○\u200b\xa0\r\n\t]+', ' ', s)
    # Retain alphanumeric
    s = re.sub(r'[^a-zA-Z0-9]+', ' ', s)
    return ' '.join(s.lower().split())


def densify_markdown_for_match(text: str | None) -> str:
    """Join short canvas/table lines so a multi-cell quote can match one span.

    Strategyzer-style canvases and pitch tables store each cell on its own line.
    The model often copies adjacent cells as one quote; densifying short lines
    restores that contiguous reading order for matching only.
    """
    if not text:
        return ""
    parts: list[str] = []
    buf: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if buf:
                parts.append(" ".join(buf))
                buf = []
            continue
        short_cell = len(line) <= 96 and not line.endswith((".", "?", "!"))
        if short_cell:
            buf.append(line)
            continue
        if buf:
            parts.append(" ".join(buf))
            buf = []
        parts.append(line)
    if buf:
        parts.append(" ".join(buf))
    return "\n".join(parts)


def _ordered_span_with_gaps(cite_words: list[str], body_words: list[str], max_gap: int = 1) -> bool:
    """True when citation words appear in order with at most max_gap tokens between each."""
    if not cite_words or not body_words:
        return False
    n = len(cite_words)
    for start in range(len(body_words)):
        if body_words[start] != cite_words[0]:
            continue
        pos = start
        ok = True
        for k in range(1, n):
            window_end = min(len(body_words), pos + 2 + max_gap)
            found = None
            for j in range(pos + 1, window_end):
                if body_words[j] == cite_words[k]:
                    found = j
                    break
            if found is None:
                ok = False
                break
            pos = found
        if ok:
            return True
    return False


def is_negative_citation(text: str | None) -> bool:
    """Check if the citation text represents a statement of absence rather than founder evidence."""
    if not text:
        return True
    text_lower = text.lower().strip()
    return any(re.search(pat, text_lower) for pat in NEGATIVE_CITATION_PATTERNS)


def is_scaffolding_citation(text: str | None) -> bool:
    """Check if the citation text contains competition template instructions or guide prompts."""
    if not text:
        return False
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in SCAFFOLDING_CITATION_PATTERNS)


def match_citation_to_text(citation: str | None, text: str | None) -> bool:
    """True when the citation is a continuous span of the founder markdown.

    Matching uses densified short lines (canvas/table cells) and allows a single
    intervening token between citation words so adjacent cells still count as one
    span. Scaffolding and evaluator-style absences are rejected.
    """
    if not citation or not citation.strip() or not text:
        return False
    if is_negative_citation(citation) or is_scaffolding_citation(citation):
        return False
    clean_cit = normalize_text(citation)
    if not clean_cit:
        return False
    densified = densify_markdown_for_match(text)
    body = normalize_text(densified)
    if clean_cit in body:
        return True
    # Fallback: order-preserving match with at most one skipped token between words.
    return _ordered_span_with_gaps(clean_cit.split(), body.split(), max_gap=1)


def match_citation_to_chunks(
    citation: str | None,
    chunks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Match a citation only when it is one continuous span of a single chunk.

    A quote of one to three words is kept when those words appear together in the
    chunk, which covers a company name. A quote of four to seven words is rejected.
    Eight or more words must appear together in that one chunk. A prefix of a
    longer quote, or two sentences joined from different places, does not match.
    """
    if not citation or not citation.strip():
        return None

    if is_negative_citation(citation) or is_scaffolding_citation(citation):
        return None

    clean_cit = normalize_text(citation)
    words = clean_cit.split()
    if not words:
        return None
    # One to three words are kept only when they are an exact token span, such as a company name.
    # Four or more words must also be an exact span. A prefix or a spliced quote is not a match.
    if len(words) > 3 and len(words) < 8:
        return None

    for chunk in chunks:
        norm = normalize_text(chunk.get("text", ""))
        if clean_cit and clean_cit in norm:
            return {
                "source_pdf": chunk.get("source_pdf"),
                "page_number": chunk.get("page_no"),
                "chunk_id": chunk.get("chunk_id"),
                "match_tier": 1,
            }

    return None


def is_engineered_rationale(text: str | None) -> bool:
    """True when rationale is a pipeline-written constant, not model diligence prose."""
    if not text or not str(text).strip():
        return False
    norm = " ".join(str(text).lower().split())
    return any(phrase in norm for phrase in ENGINEERED_RATIONALE_PHRASES)


def is_junk_micro_citation(text: str | None) -> bool:
    """True for denylisted / non-entity micro-stubs (NA, No, markdown-only, canvas headers)."""
    if not text or not str(text).strip():
        return False
    raw = str(text).strip()
    if raw == "None.":
        return False
    # Markdown-only / heading-only stubs
    if re.fullmatch(r"[#*_`~\-\s.]+", raw):
        return True
    if re.fullmatch(r"#{1,6}\s+\S+", raw) and len(raw.split()) <= 3:
        return True
    norm = normalize_text(raw)
    if not norm:
        return True
    if norm in JUNK_MICRO_CITATION_NORMS:
        return True
    # Single generic tokens
    if norm in {"diagram", "table", "figure", "image", "slide", "header"}:
        return True
    return False


_LEGAL_ENTITY_NORMS = frozenset({
    "c corp", "s corp", "llc", "l l c", "inc", "ltd", "gmbh", "plc", "llp",
    "pc", "pa", "delaware llc", "delaware c corp", "b corp",
})


def is_entity_short_cite(text: str | None) -> bool:
    """True when a 1–3 word citation looks like a proper name / org, not junk."""
    if not text or not str(text).strip():
        return False
    if is_junk_micro_citation(text):
        return False
    raw = str(text).strip()
    norm = normalize_text(raw)
    if norm in _LEGAL_ENTITY_NORMS:
        return True
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9&.'/-]*", raw)
    if not words or len(words) > 3:
        return False
    # At least one capitalized / alphanumeric proper-ish token of length >= 2
    for w in words:
        core = re.sub(r"[^A-Za-z0-9]", "", w)
        if len(core) >= 2 and (core[0].isupper() or core.isupper() or any(ch.isdigit() for ch in core)):
            return True
    return False


class QuestionEvaluation(BaseModel):
    """Schema for individual rubric question evaluation."""
    q_id: str
    predicted_val: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    citation: str | None = None
    source_pdf: str | None = None
    page_number: int | None = None
    rationale: str | None = None
    error_code: str | None = None

    @field_validator("citation")
    @classmethod
    def sanitize_citation(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        v_clean = v.strip()
        # Allow short exact tokens such as a company name; reject junk micro-stubs.
        if (
            len(v_clean) < 2
            or is_negative_citation(v_clean)
            or is_scaffolding_citation(v_clean)
            or is_junk_micro_citation(v_clean)
        ):
            return None
        return v_clean

    @field_validator("error_code")
    @classmethod
    def validate_error_code(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        code = str(v).strip().upper()
        if code not in ERROR_CODES:
            raise ValueError(f"error_code must be one of {ERROR_CODES}")
        return code


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
        description="2-3 sentences naming concrete founder content from the citation before the verdict"
    )

    @field_validator("citation")
    @classmethod
    def sanitize_citation(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        v_clean = v.strip()
        if (
            len(v_clean) < 2
            or is_negative_citation(v_clean)
            or is_scaffolding_citation(v_clean)
            or is_junk_micro_citation(v_clean)
        ):
            return None
        return v_clean

