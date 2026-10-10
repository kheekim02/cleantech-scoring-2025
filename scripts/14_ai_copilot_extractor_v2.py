"""High-Throughput Grounded Diligence Extractor v2 (parsed markdown + Ollama/SGLang).

Scores clean startup applications against the 282-criteria rubric using continuous
founder markdown from parsed_clean_v4. Citations must be exact spans of primary
documents. PDF page provenance is not produced in this generation.
"""
import os
import sys
import time
import json
import logging
import argparse
import re
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import instructor
    from openai import OpenAI
except ImportError:  # Ollama scoring does not need the Instructor client.
    instructor = None
    OpenAI = None

from src.scorer.schemas import (
    QuestionEvaluation,
    RawModelExtraction,
    match_citation_to_text,
    normalize_text,
)
from src.scorer.deterministic_evaluator import DETERMINISTIC_RULES, find_deterministic_evidence
from scripts.audit_v5_parsed import SDG_QUESTION_RE, audit_parsed_records
from scripts.docling_ingestion import resolve_doc_type

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extractor_v2")

ABSENCE_RE = re.compile(
    r"((?:does|do)\s+not\s+(?:state|mention|provide|include|contain|specify)|"
    r"no\s+(?:mention|evidence|information|discussion)|"
    r"not\s+(?:explicitly\s+)?(?:stated|mentioned|provided)|"
    r"absent|missing\s+from\s+the\s+document|"
    r"provided\s+documents?\s+contain\s+no)",
    re.IGNORECASE,
)
RETRYABLE_ERROR_CODES = {
    "WITHHELD_SCORE_ABSENCE_MISMATCH",
    "WITHHELD_UNSUPPORTED_CLAIM",
}

DEFAULT_SGLANG_URL = os.environ.get("SGLANG_BASE_URL", "http://127.0.0.1:30000")
DEFAULT_RUBRIC_PATH = "master_282_rubric.json"
REMOTE_DATASET_ROOT = "/data/scraping/datasets/cto_accelerator"
REMOTE_PARSED_DIR = os.path.join(REMOTE_DATASET_ROOT, "parsed_clean_v4")
SHADOW_CACHE_NAME = "ai_cache_v5_parsed"
ALLOWLIST_NAME = "active_startup_allowlist.json"
# Kept for tests and legacy callers that still pass a chunks directory.
REMOTE_DOCLING_DIR = "/data/scraping/data/docling_clean_v4"
DEFAULT_RAW_DIR = os.path.join(REMOTE_DATASET_ROOT, "raw")


def default_parsed_dir() -> str:
    """Continuous cleaned markdown for the live cohort."""
    if os.path.isdir(REMOTE_PARSED_DIR):
        return REMOTE_PARSED_DIR
    local = os.path.join("data", "parsed_clean_v4")
    if os.path.isdir(local):
        return local
    return local


def default_docling_dir() -> str:
    """Legacy Docling path retained for older helpers and tests."""
    if os.path.isdir(REMOTE_DATASET_ROOT):
        os.makedirs(REMOTE_DOCLING_DIR, exist_ok=True)
        return REMOTE_DOCLING_DIR
    return "data/docling_clean_v4"


def default_cache_dir() -> str:
    """Write parsed-markdown scores beside v3_strict, never into Docling-era caches."""
    if os.path.isdir(REMOTE_DATASET_ROOT):
        return os.path.join(REMOTE_DATASET_ROOT, SHADOW_CACHE_NAME)
    return os.path.join("data", SHADOW_CACHE_NAME)


def load_active_allowlist(explicit: str | None = None) -> tuple[list[str], str]:
    """Load the live cohort. Missing file fails closed so raw/ is not scanned."""
    repo_data = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        ALLOWLIST_NAME,
    )
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    candidates.extend([
        os.path.join("data", ALLOWLIST_NAME),
        repo_data,
        os.path.join(REMOTE_DATASET_ROOT, ALLOWLIST_NAME),
    ])
    seen: set[str] = set()
    for path in candidates:
        if not path or path in seen:
            continue
        seen.add(path)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        ids = [row["startup_id"] for row in payload["startups"]]
        if len(ids) != payload.get("count"):
            raise ValueError(
                f"Allowlist count mismatch in {path}: {len(ids)} != {payload.get('count')}"
            )
        return ids, path
    raise FileNotFoundError(
        "Active startup allowlist not found. Refusing to scan raw/. Looked in: "
        + ", ".join(candidates)
    )


DEFAULT_CACHE_DIR = default_cache_dir()
DEFAULT_DOCLING_DIR = default_docling_dir()
DEFAULT_PARSED_DIR = default_parsed_dir()


def get_active_model_id(sglang_url: str) -> str:
    """Fetch active model ID from SGLang /v1/models."""
    url = f"{sglang_url}/v1/models"
    req = urllib.request.Request(url, headers={"User-Agent": "CTO-Extractor/2.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        return data["data"][0]["id"]


def create_instructor_client(sglang_url: str, timeout: int = 60) -> Any:
    """Create Instructor client wrapping OpenAI client pointing to SGLang."""
    if instructor is None or OpenAI is None:
        raise RuntimeError("Instructor is not installed")
    openai_client = OpenAI(
        base_url=f"{sglang_url}/v1",
        api_key="EMPTY",
        timeout=timeout,
    )
    client = instructor.from_openai(openai_client, mode=instructor.Mode.JSON)
    client._base_url_str = sglang_url
    return client


# ES questions are SDGs, climate, and waste, so the impact statement and GHG module
# are primary. IS questions open with company name, contact, and logo, so the
# one-page executive summary is primary. Only those primary chunks are sent.
CAT_PRIMARY_SOURCES: dict[str, list[str]] = {
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

CAT_FALLBACK_SOURCES: dict[str, list[str]] = {
    "PMF": ["EBD1", "EBD8"],
    "M": ["EBD1", "EBD8"],
    "BC": ["EBD8"],
    "IS": ["EBD8"],
}
# Fits a 32,768-token model window with room for the question and the answer.
CONTEXT_CHAR_LIMIT = 80_000

# Optgroup labels in site/js/render.js categoryNames. The dropdown uses these
# labels, not the payload section heading.
INTERFACE_CATEGORY_LABELS: dict[str, str] = {
    "BC": "Business Canvas",
    "ES": "Environmental & Social",
    "F": "Financials",
    "IP": "Investor Pitch",
    "IS": "Impact Strategy",
    "L": "Legal",
    "M": "Marketing",
    "PMF": "Product Market Fit",
    "T": "Team",
    "TP": "Tech / Product",
}


def interface_categories_for_doc_type(doc_type: str) -> list[str]:
    """Rubric categories that treat this deliverable as a primary source."""
    return [cat for cat, types in CAT_PRIMARY_SOURCES.items() if doc_type in types]


def build_doc_manifest(chunks: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build a mapping from doc_type code to list of unique source_pdf filenames.

    This gives the extractor the exact filenames present for each deliverable
    category so the system prompt can reference them by name.
    """
    manifest: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        doc_type = chunk.get("doc_type", "OTHER")
        source_pdf = chunk.get("source_pdf", "")
        if not source_pdf or (doc_type, source_pdf) in seen:
            continue
        seen.add((doc_type, source_pdf))
        manifest.setdefault(doc_type, []).append(source_pdf)
    return manifest


def load_parsed_documents(startup_parsed_dir: str | Path) -> list[dict[str, Any]]:
    """Load cleaned *.pdf.md files and classify each with the shared resolver."""
    root = Path(startup_parsed_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Parsed directory not found for startup at {root}")
    docs: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.pdf.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        # Stem is like 03_CarbonDots-BMC-8June.pdf.md -> classify as the PDF name.
        pdf_name = path.name[:-3] if path.name.endswith(".md") else path.name
        if pdf_name.endswith(".pdf"):
            pass
        elif path.name.endswith(".pdf.md"):
            pdf_name = path.name[: -len(".md")]
        doc_type = resolve_doc_type(pdf_name, text[:1200])
        docs.append({
            "source_pdf": pdf_name,
            "doc_type": doc_type,
            "text": text,
            "path": str(path),
        })
    return docs


def build_doc_manifest_from_docs(docs: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map doc_type -> markdown source filenames for the system prompt."""
    manifest: dict[str, list[str]] = {}
    for doc in docs:
        doc_type = doc.get("doc_type", "OTHER")
        name = doc.get("source_pdf") or ""
        if not name:
            continue
        bucket = manifest.setdefault(doc_type, [])
        if name not in bucket:
            bucket.append(name)
    return manifest


def _chunk_block(chunk: dict[str, Any]) -> str:
    page = chunk.get("page_no") or chunk.get("page_number")
    page_info = f"[Page {page}] " if page else ""
    return f"{page_info}{chunk.get('text', '')}".strip()


def build_category_context(
    chunks: list[dict[str, Any]],
    cat_code: str,
    char_limit: int = CONTEXT_CHAR_LIMIT,
) -> dict[str, Any]:
    """Send primary deliverables only, stopping on a chunk boundary.

    Secondary documents are omitted. A chunk that would cross the character
    budget is left out whole, so the model never sees a sentence cut in half.
    A category with no classified primary file is not scored.
    """
    primary_types = set(CAT_PRIMARY_SOURCES.get(cat_code, []))
    by_file: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for chunk in chunks:
        fname = chunk.get("source_pdf") or ""
        if fname not in by_file:
            by_file[fname] = []
            order.append(fname)
        by_file[fname].append(chunk)

    primary_files = [
        fname for fname in order if by_file[fname][0].get("doc_type") in primary_types
    ]
    is_fallback = False
    if not primary_files:
        fallback_types = set(CAT_FALLBACK_SOURCES.get(cat_code, []))
        if fallback_types:
            primary_files = [
                fname for fname in order if by_file[fname][0].get("doc_type") in fallback_types
            ]
            if primary_files:
                is_fallback = True

    pieces: list[str] = []
    used = 0

    def add_file(fname: str) -> bool:
        nonlocal used
        file_chunks = by_file[fname]
        role_label = "FALLBACK" if is_fallback else "PRIMARY"
        header = (
            f"=== DOCUMENT: {fname} "
            f"[Type: {file_chunks[0].get('doc_type', 'OTHER')}] [Role: {role_label}] ==="
        )
        if used + len(header) > char_limit:
            return False
        parts = [header]
        cursor = used + len(header)
        added_body = False
        for chunk in file_chunks:
            block = _chunk_block(chunk)
            if not block:
                continue
            if cursor + 2 + len(block) > char_limit:
                break
            parts.append(block)
            cursor += 2 + len(block)
            added_body = True
        if not added_body:
            return False
        pieces.append("\n\n".join(parts))
        used = cursor + 3
        return cursor + 3 < char_limit

    for fname in primary_files:
        if not add_file(fname):
            break

    return {
        "text": "\n\n\n".join(pieces),
        "has_primary": bool(primary_files),
        "primary_filenames": primary_files,
        "primary_text": "\n\n".join(
            "\n\n".join(_chunk_block(c) for c in by_file[fname] if _chunk_block(c))
            for fname in primary_files
        ),
        "is_fallback": is_fallback,
    }


def build_category_context_from_docs(
    docs: list[dict[str, Any]],
    cat_code: str,
    char_limit: int = CONTEXT_CHAR_LIMIT,
) -> dict[str, Any]:
    """Primary-only context from continuous parsed markdown files.

    Whole files are preferred. If a file would exceed the remaining budget it is
    omitted entirely unless it is the first primary file, in which case the file
    is trimmed on a paragraph boundary.
    """
    primary_types = set(CAT_PRIMARY_SOURCES.get(cat_code, []))
    primary_docs = [doc for doc in docs if doc.get("doc_type") in primary_types]
    is_fallback = False

    if not primary_docs:
        fallback_types = set(CAT_FALLBACK_SOURCES.get(cat_code, []))
        if fallback_types:
            primary_docs = [doc for doc in docs if doc.get("doc_type") in fallback_types]
            if primary_docs:
                is_fallback = True

    pieces: list[str] = []
    body_parts: list[str] = []
    used = 0

    for index, doc in enumerate(primary_docs):
        fname = doc.get("source_pdf") or "unknown"
        body = (doc.get("text") or "").strip()
        if not body:
            continue
        role_label = "FALLBACK" if is_fallback else "PRIMARY"
        header = f"=== DOCUMENT: {fname} [Type: {doc.get('doc_type', 'OTHER')}] [Role: {role_label}] ==="
        block = f"{header}\n\n{body}"
        if used + len(block) + (3 if pieces else 0) <= char_limit:
            pieces.append(block)
            body_parts.append(body)
            used += len(block) + (3 if len(pieces) > 1 else 0)
            continue
        if index == 0 and not pieces:
            remain = char_limit - len(header) - 2
            trimmed = _trim_on_boundary(body, max(0, remain))
            if trimmed:
                pieces.append(f"{header}\n\n{trimmed}")
                body_parts.append(trimmed)
        break

    return {
        "text": "\n\n\n".join(pieces),
        "has_primary": bool(primary_docs),
        "primary_filenames": [doc.get("source_pdf") or "unknown" for doc in primary_docs],
        "primary_text": "\n\n".join(body_parts),
        "is_fallback": is_fallback,
    }


def _trim_on_boundary(text: str, limit: int) -> str:
    """Drop a tail that crosses the budget, cutting at a paragraph break."""
    if len(text) <= limit:
        return text
    cut = text.rfind("\n\n", 0, limit)
    return text[:cut] if cut > 0 else ""


def _is_ollama(url: str | None) -> bool:
    if not url:
        return False
    return ":11434" in url or ":11435" in url


def _ollama_root(url: str) -> str:
    root = url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    return root


def _parse_model_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("model response was not a JSON object")
    return parsed


def _ollama_chat(
    endpoint: str,
    model_id: str,
    messages: list[dict[str, str]],
    timeout: int,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Ask Ollama with thinking disabled so the answer is the message content."""
    payload = json.dumps({
        "model": model_id,
        "think": False,
        "stream": False,
        "options": {"temperature": float(temperature), "num_predict": 500, "num_ctx": 32768},
        "messages": messages,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{_ollama_root(endpoint)}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    content = ((data.get("message") or {}).get("content") or "").strip()
    if not content:
        raise ValueError("ollama returned empty content")
    return _parse_model_json(content)


def _error_code_for(findings: list[dict[str, str]]) -> str:
    checks = {item.get("check") for item in findings}
    if checks & {"timeout"}:
        return "TIMEOUT"
    if checks & {"no_primary"}:
        return "NO_PRIMARY"
    if checks & {"score_absence_mismatch"}:
        return "WITHHELD_SCORE_ABSENCE_MISMATCH"
    if checks & {"rationale_unsupported", "score_without_sdg", "rationale_generic"}:
        return "WITHHELD_UNSUPPORTED_CLAIM"
    if checks & {
        "citation_ungrounded",
        "citation_not_primary",
        "citation_template",
        "citation_missing",
        "schema",
    }:
        return "WITHHELD_UNGROUNDED"
    return "WITHHELD_UNGROUNDED"


def _withhold(qid: str, findings: list[dict[str, str]], error_code: str | None = None) -> dict[str, Any]:
    """Drop the score without persisting human-looking withhold prose as a rationale."""
    code = error_code or _error_code_for(findings)
    return {
        "q_id": qid,
        "predicted_val": None,
        "confidence": 0.0,
        "citation": None,
        "source_pdf": None,
        "page_number": None,
        "rationale": None,
        "error_code": code,
    }


def _is_zero_score(score: Any) -> bool:
    return score is not None and round(float(score), 2) == 0.0


def _rationale_shares_citation_token(rationale: str | None, citation: str | None, company: str | None = None) -> bool:
    """Non-zero scores need rationale content grounded in the citation or company name."""
    rat_toks = set(normalize_text(rationale).split())
    if not rat_toks:
        return False
    cite_toks = set(normalize_text(citation).split())
    if cite_toks & rat_toks:
        return True
    if company:
        company_toks = {t for t in normalize_text(company).split() if len(t) >= 3}
        if company_toks & rat_toks:
            return True
    return False


def accept_model_answer(
    raw: dict[str, Any],
    primary_text: str,
    question: dict[str, Any],
    company: str | None = None,
) -> dict[str, Any]:
    """Keep a score when the quote is exact primary markdown (or a bare zero).

    PDF provenance is not stored. A non-zero score requires a grounded citation.
    Invented figures, absence/score mismatches, and generic rationales withhold
    with a structured error_code — never a constant clone rationale string.
    """
    # Passthrough structured operational withholds from the query path.
    if raw.get("error_code") in {"TIMEOUT", "NO_PRIMARY"}:
        return {
            "q_id": question.get("new_q_id") or question.get("q_id") or raw.get("q_id"),
            "predicted_val": None,
            "confidence": 0.0,
            "citation": None,
            "source_pdf": None,
            "page_number": None,
            "rationale": None,
            "error_code": raw["error_code"],
        }

    qid = question.get("new_q_id") or question.get("q_id") or raw.get("q_id")
    cat = question.get("cat_code") or str(qid or "").split("_")[0]
    score = raw.get("predicted_val")
    citation = raw.get("citation")
    rationale = raw.get("rationale")
    grounded = match_citation_to_text(citation, primary_text) if citation else False

    if citation and not grounded:
        if _is_zero_score(score):
            citation = None
        else:
            return _withhold(qid, [{"check": "citation_ungrounded", "detail": f"{qid} citation ungrounded"}])

    if score is not None and not _is_zero_score(score) and not citation:
        return _withhold(qid, [{"check": "citation_missing", "detail": f"{qid} missing citation"}])

    # G2.3: absence language cannot accompany a mid/high score.
    if (
        rationale
        and ABSENCE_RE.search(str(rationale))
        and score is not None
        and round(float(score), 2) >= 0.5
    ):
        return _withhold(
            qid,
            [{"check": "score_absence_mismatch", "detail": f"{qid} absence language with score {score}"}],
        )

    record = {
        "q_id": qid,
        "predicted_val": score,
        "confidence": 0.0 if raw.get("confidence") is None else raw.get("confidence"),
        "citation": citation if grounded else None,
        "source_pdf": None,
        "page_number": None,
        "rationale": rationale,
        "error_code": None,
    }
    try:
        validated = QuestionEvaluation(**record).model_dump()
    except Exception as exc:
        logger.info("Schema rejected %s: %s", qid, exc)
        return _withhold(qid, [{"check": "schema", "detail": str(exc)}])

    # Schema may drop a short citation; treat like missing for non-zero scores.
    if validated.get("predicted_val") is not None and not _is_zero_score(validated.get("predicted_val")):
        if not validated.get("citation"):
            return _withhold(qid, [{"check": "citation_missing", "detail": f"{qid} citation dropped by schema"}])

    # Non-zero scores need company/citation-grounded rationale content.
    if (
        company is not None
        and validated.get("predicted_val") is not None
        and not _is_zero_score(validated.get("predicted_val"))
        and not _rationale_shares_citation_token(
            validated.get("rationale"),
            validated.get("citation"),
            company,
        )
    ):
        return _withhold(
            qid,
            [{"check": "rationale_generic", "detail": f"{qid} rationale lacks citation/company tokens"}],
        )

    findings = audit_parsed_records(
        [validated],
        {cat: primary_text},
        [question],
    )
    if findings:
        checks = {f.get("check") for f in findings}
        is_sdg_q = bool(SDG_QUESTION_RE.search(question.get("text", ""))) or str(qid).startswith("ES_Q1")
        if company is None and is_sdg_q and checks <= {"rationale_unsupported", "score_without_sdg"}:
            clean_rat = re.sub(r"(?i)\bsdg\s*\d+\b", "", validated.get("rationale") or "")
            clean_rat = re.sub(r"(?i)\bsdgs?\b", "sustainability goals", clean_rat)
            clean_rat = re.sub(r"\s*,\s*", ", ", clean_rat)
            clean_rat = re.sub(r",\s*and\b", " and", clean_rat)
            clean_rat = re.sub(r"\b(and\s*)+", "and ", clean_rat)
            clean_rat = re.sub(r"\s+", " ", clean_rat).strip()
            clean_rat = re.sub(r"(?i)sdg", "", clean_rat).strip()
            clean_rat = re.sub(r"\s+", " ", clean_rat).strip()
            if not clean_rat or clean_rat in {".", "This .", "This aligns .", "This addresses .", "This aligns with .", "This addresses."}:
                clean_rat = "The company purpose describes environmental and social impact but does not reference specific sustainable development goals in the primary text."
            validated["predicted_val"] = 0.0
            validated["rationale"] = clean_rat
            validated["source_pdf"] = None
            validated["page_number"] = None
            validated["error_code"] = None
            return validated
        # Inventing figures / SDG soft-fails used to sanitize to a constant string.
        # That manufactured cross-company clones — withhold instead.
        logger.info("Withheld %s: %s", qid, findings[0]["detail"])
        return _withhold(qid, findings)
    validated["source_pdf"] = None
    validated["page_number"] = None
    validated["error_code"] = None
    return validated


POLICY_PATH = Path(__file__).resolve().parent.parent / "data" / "category_policies.json"


def load_policies(path: str | None = None) -> dict[str, dict[str, str]]:
    p = Path(path) if path else POLICY_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    return {"category": data.get("category", {}), "question": data.get("question", {})}


def build_system_prompt(
    question: dict[str, Any], doc_manifest: dict[str, list[str]] | None, policies: dict[str, dict[str, str]]
) -> str:
    qid = question.get("new_q_id", question.get("q_id"))
    cat_code = question.get("cat_code", "GENERAL")
    primary_filenames: list[str] = []
    if doc_manifest and cat_code in CAT_PRIMARY_SOURCES:
        for tc in CAT_PRIMARY_SOURCES[cat_code]:
            primary_filenames.extend(doc_manifest.get(tc, []))
    file_list = ", ".join(f'"{f}"' for f in primary_filenames) if primary_filenames else "the documents marked [Role: PRIMARY]"
    sourcing_instruction = (
        f"For this {cat_code} criterion, quote only from these PRIMARY documents: {file_list}. "
        "Copy one unbroken contiguous region of founder text exactly as it appears. "
        "Do not paraphrase, splice distant sentences, or join table cells with pipes. "
        "If evidence is on separate short lines, copy those lines in document order with spaces only. "
        "The rationale may only repeat facts that appear in that span. "
        "Do not name an SDG number, dollar amount, or percentage unless those characters appear in the quote."
    )
    sourcing_instruction += policies["category"].get(cat_code, "")
    sourcing_instruction += policies["question"].get(str(qid), "")
    return (
        "You are an objective due diligence evaluator scoring cleantech startup applications. "
        "Strictly adhere to the provided rubric and only quote verbatim text written by founders. "
        "Do NOT quote instructions or template boilerplate. "
        f"{sourcing_instruction}"
    )


_POLICIES = load_policies()


def query_sglang_question(
    client: Any,
    model_id: str,
    prefix_context: str,
    question: dict[str, Any],
    timeout: int = 60,
    doc_manifest: dict[str, list[str]] | None = None,
    has_primary: bool = True,
    endpoint: str | None = None,
    startup_id: str | None = None,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Execute evaluation for a single rubric question against the cached prefix context using Instructor."""
    qid = question.get("new_q_id", question.get("q_id"))
    options = [o.get("val") for o in question.get("options", [])]
    options_desc = ", ".join(str(o) for o in options) if options else "0.0, 1.0"
    company_label = startup_id or "this startup"

    cat_code = question.get('cat_code', 'GENERAL')
    if not has_primary:
        return {
            "q_id": qid,
            "predicted_val": None,
            "confidence": 0.0,
            "citation": None,
            "rationale": "No primary source document was classified for this category.",
            "error_code": "NO_PRIMARY",
            "duration_sec": 0.0,
        }

    system_prompt = build_system_prompt(question, doc_manifest, _POLICIES)

    # The category builder already stops on a chunk boundary. This only drops a tail
    # that somehow still crosses the budget, and it drops that tail at a break.
    safe_context = _trim_on_boundary(prefix_context, CONTEXT_CHAR_LIMIT)
    user_prompt = (
        f"<applicant_prose>\n{safe_context}\n</applicant_prose>\n\n"
        f"<rubric_criterion>\n"
        f"ID: {qid}\n"
        f"Company: {company_label}\n"
        f"Category: {question.get('cat_code', 'GENERAL')}\n"
        f"Text: {question.get('text', '')}\n"
        f"Allowed Scoring Options: [{options_desc}]\n"
        f"</rubric_criterion>\n\n"
        f"Output ONLY a valid JSON object matching this schema:\n"
        f"{{\n"
        f'  "q_id": "{qid}",\n'
        f'  "predicted_val": <one number chosen strictly from Allowed Scoring Options, or null if no evidence>,\n'
        f'  "confidence": <float 0.0 to 1.0>,\n'
        f'  "citation": <exact continuous verbatim span copied from applicant_prose, or null if no evidence>,\n'
        f'  "rationale": <2-3 sentences naming concrete founder content from the citation before the verdict; '
        f'if no evidence, set predicted_val to 0.0, citation to null, and write one sentence naming the missing '
        f'artifact type AND the company name "{company_label}">\n'
        f"}}"
    )

    t0 = time.perf_counter()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    resolved_endpoint = endpoint or (getattr(client, "_base_url_str", None) if client else None) or DEFAULT_SGLANG_URL
    if _is_ollama(resolved_endpoint):
        for attempt in range(3):
            try:
                parsed = _ollama_chat(
                    resolved_endpoint, model_id, messages, timeout, temperature=temperature
                )
                parsed["q_id"] = parsed.get("q_id") or qid
                parsed["duration_sec"] = round(time.perf_counter() - t0, 3)
                return parsed
            except Exception as e:
                if attempt == 2:
                    logger.warning(f"Ollama request failed on {qid}: {e}")
                time.sleep(0.5)
        return {
            "q_id": qid,
            "predicted_val": None,
            "confidence": 0.0,
            "citation": None,
            "rationale": None,
            "error_code": "TIMEOUT",
            "duration_sec": round(time.perf_counter() - t0, 3),
        }

    if client is not None:
        try:
            extraction: RawModelExtraction = client.chat.completions.create(
                model=model_id,
                response_model=RawModelExtraction,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=float(temperature),
                max_tokens=350,
                max_retries=2,
            )
            return {
                "q_id": qid,
                "predicted_val": extraction.predicted_val,
                "confidence": extraction.confidence,
                "citation": extraction.citation,
                "rationale": extraction.rationale,
                "duration_sec": round(time.perf_counter() - t0, 3),
            }
        except Exception as e:
            logger.warning(f"Instructor extraction warning on {qid}: {e}; trying fallback")

    # Fallback via direct HTTP request if client was None or failed
    sglang_url = getattr(client, "_base_url_str", DEFAULT_SGLANG_URL) if client else DEFAULT_SGLANG_URL
    payload = json.dumps({
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": float(temperature),
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{sglang_url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                content = data["choices"][0]["message"]["content"].strip()

                # Parse JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                parsed = json.loads(content)
                parsed["duration_sec"] = round(time.perf_counter() - t0, 3)
                return parsed
        except Exception as e:
            if attempt == 2:
                logger.warning(f"Failed question {qid} after fallback attempts: {e}")
            time.sleep(0.5)

    return {
        "q_id": qid,
        "predicted_val": None,
        "confidence": 0.0,
        "citation": None,
        "rationale": None,
        "error_code": "TIMEOUT",
        "duration_sec": round(time.perf_counter() - t0, 3),
    }


def deterministic_answer(question: dict[str, Any], primary_text: str, company: str) -> dict[str, Any] | None:
    """Positive-only structured answer. Regex absence never produces a score."""
    qid = question.get("new_q_id") or question.get("q_id")
    allowed = {round(float(o.get("val")), 2) for o in question.get("options") or [] if o.get("val") is not None}
    if allowed and 1.0 not in allowed:
        return None
    span = find_deterministic_evidence(qid, primary_text)
    if not span:
        return None
    raw = {
        "q_id": qid,
        "predicted_val": 1.0,
        "confidence": 0.95,
        "citation": span,
        "rationale": f"{company} primary text states: {span} {DETERMINISTIC_RULES[qid]['label']}.",
    }
    rec = accept_model_answer(raw, primary_text, question, company=company)
    if rec.get("error_code") or rec.get("predicted_val") != 1.0:
        return None
    rec["source"] = "deterministic"
    return rec


def score_question(
    question: dict[str, Any],
    ctx: dict[str, Any],
    *,
    query_fn: Any,
    client: Any,
    model_id: str,
    timeout: int,
    doc_manifest: dict[str, list[str]],
    endpoint: str,
    startup_id: str,
) -> dict[str, Any]:
    primary_text = ctx.get("primary_text", "")
    has_primary = ctx.get("has_primary", False)
    if has_primary:
        det = deterministic_answer(question, primary_text, startup_id)
        if det is not None:
            return det

    def _ask(temperature: float) -> dict[str, Any]:
        raw = query_fn(client, model_id, ctx.get("text", ""), question, timeout, doc_manifest,
                       has_primary, endpoint, startup_id=startup_id, temperature=temperature)
        return accept_model_answer(raw, primary_text, question, company=startup_id)

    rec = _ask(0.0)
    if rec.get("error_code") in RETRYABLE_ERROR_CODES:
        rec = _ask(0.2)
    return rec


def group_questions(questions: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size <= 1:
        return [[x] for x in questions]
    by_cat: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for x in questions:
        cat = x.get("cat_code") or ""
        if cat not in by_cat:
            by_cat[cat] = []
            order.append(cat)
        by_cat[cat].append(x)
    groups: list[list[dict[str, Any]]] = []
    for cat in order:
        items = by_cat[cat]
        groups.extend(items[i:i + batch_size] for i in range(0, len(items), batch_size))
    return groups


def split_batched_response(raw_items: list[dict[str, Any]], group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = [x.get("new_q_id") or x.get("q_id") for x in group]
    seen: dict[str, list[dict[str, Any]]] = {}
    for item in raw_items or []:
        if isinstance(item, dict) and item.get("q_id") in wanted:
            seen.setdefault(item["q_id"], []).append(item)
    out: list[dict[str, Any]] = []
    for qid in wanted:
        hits = seen.get(qid, [])
        if len(hits) == 1:
            out.append(dict(hits[0]))
        else:
            out.append({"q_id": qid, "predicted_val": None, "confidence": 0.0, "citation": None,
                        "rationale": None, "error_code": "TIMEOUT"})
    return out


def query_batch(
    client: Any,
    model_id: str,
    prefix_context: str,
    group: list[dict[str, Any]],
    timeout: int = 60,
    doc_manifest: dict[str, list[str]] | None = None,
    has_primary: bool = True,
    endpoint: str | None = None,
    startup_id: str | None = None,
    temperature: float = 0.0,
) -> list[dict[str, Any]]:
    if not group:
        return []
    if not has_primary:
        return [
            {
                "q_id": q.get("new_q_id") or q.get("q_id"),
                "predicted_val": None,
                "confidence": 0.0,
                "citation": None,
                "rationale": "No primary source document was classified for this category.",
                "error_code": "NO_PRIMARY",
                "duration_sec": 0.0,
            }
            for q in group
        ]

    company_label = startup_id or "this startup"
    system_prompt = build_system_prompt(group[0], doc_manifest, _POLICIES)
    safe_context = _trim_on_boundary(prefix_context, CONTEXT_CHAR_LIMIT)

    criteria_blocks = []
    for q in group:
        qid = q.get("new_q_id") or q.get("q_id")
        options = [o.get("val") for o in q.get("options", [])]
        options_desc = ", ".join(str(o) for o in options) if options else "0.0, 1.0"
        criteria_blocks.append(
            f"<rubric_criterion>\n"
            f"ID: {qid}\n"
            f"Company: {company_label}\n"
            f"Category: {q.get('cat_code', 'GENERAL')}\n"
            f"Text: {q.get('text', '')}\n"
            f"Allowed Scoring Options: [{options_desc}]\n"
            f"</rubric_criterion>"
        )

    user_prompt = (
        f"<applicant_prose>\n{safe_context}\n</applicant_prose>\n\n"
        + "\n\n".join(criteria_blocks)
        + "\n\nOutput ONLY a valid JSON object with an 'answers' list matching this schema:\n"
        '{\n  "answers": [\n    {\n'
        '      "q_id": "<criterion ID>",\n'
        '      "predicted_val": <one number chosen strictly from Allowed Scoring Options, or null if no evidence>,\n'
        '      "confidence": <float 0.0 to 1.0>,\n'
        '      "citation": <exact continuous verbatim span copied from applicant_prose, or null if no evidence>,\n'
        '      "rationale": <2-3 sentences naming concrete founder content from the citation before the verdict; '
        f'if no evidence, set predicted_val to 0.0, citation to null, and write one sentence naming the missing '
        f'artifact type AND the company name "{company_label}">\n'
        "    }\n  ]\n}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    resolved_endpoint = endpoint or (getattr(client, "_base_url_str", None) if client else None) or DEFAULT_SGLANG_URL
    max_tokens = 350 * len(group)

    raw_items: list[dict[str, Any]] = []
    if _is_ollama(resolved_endpoint):
        for attempt in range(3):
            try:
                parsed = _ollama_chat(
                    resolved_endpoint, model_id, messages, timeout, temperature=temperature
                )
                if isinstance(parsed, dict) and "answers" in parsed and isinstance(parsed["answers"], list):
                    raw_items = parsed["answers"]
                    break
            except Exception as e:
                if attempt == 2:
                    logger.warning(f"Ollama batch request failed: {e}")
                time.sleep(0.5)
    else:
        payload = json.dumps({
            "model": model_id,
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{resolved_endpoint}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode())
                    content = data["choices"][0]["message"]["content"].strip()
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "answers" in parsed and isinstance(parsed["answers"], list):
                        raw_items = parsed["answers"]
                        break
            except Exception as e:
                if attempt == 2:
                    logger.warning(f"Failed batch request after attempts: {e}")
                time.sleep(0.5)

    return split_batched_response(raw_items, group)


def evaluate_startup(
    startup_id: str,
    sglang_url: str = DEFAULT_SGLANG_URL,
    rubric_path: str = DEFAULT_RUBRIC_PATH,
    parsed_base_dir: str = DEFAULT_PARSED_DIR,
    cache_base_dir: str = DEFAULT_CACHE_DIR,
    limit: int | None = None,
    concurrency: int = 10,
    model_id: str | None = None,
    question_ids: list[str] | None = None,
    timeout: int = 300,
    batch_size: int = 1,
    **_legacy_kwargs: Any,
) -> dict[str, Any]:
    """Score one startup from parsed_clean_v4 markdown with no PDF provenance."""
    start_time = time.time()
    logger.info(f"=== Evaluating Startup: {startup_id} (parsed markdown) ===")

    startup_parsed_dir = Path(parsed_base_dir) / startup_id
    docs = load_parsed_documents(startup_parsed_dir)
    if not docs:
        raise FileNotFoundError(f"No *.pdf.md files under {startup_parsed_dir}")

    doc_manifest = build_doc_manifest_from_docs(docs)
    category_contexts = {
        cat: build_category_context_from_docs(docs, cat) for cat in CAT_PRIMARY_SOURCES
    }
    logger.info(
        "Loaded %s markdown files | Document manifest: %s",
        len(docs),
        {k: v for k, v in sorted(doc_manifest.items())},
    )
    for cat, ctx in category_contexts.items():
        logger.info(
            "Context %s primary=%s files=%s chars=%s",
            cat,
            ctx["has_primary"],
            ctx["primary_filenames"],
            len(ctx["text"]),
        )

    rubric_candidates = [
        rubric_path,
        "master_282_rubric.json",
        "/data/scraping/master_282_rubric.json",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "master_282_rubric.json"),
    ]
    resolved_rubric_path = next((p for p in rubric_candidates if p and os.path.exists(p)), None)
    if not resolved_rubric_path:
        raise FileNotFoundError(f"Rubric file not found at any candidate: {rubric_candidates}")
    with open(resolved_rubric_path, "r", encoding="utf-8") as f:
        rubric = json.load(f)

    if question_ids:
        wanted = {qid.strip() for qid in question_ids if qid and qid.strip()}
        rubric = [q for q in rubric if (q.get("new_q_id") or q.get("q_id")) in wanted]

    if limit:
        rubric = rubric[:limit]

    cache_dir = Path(cache_base_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{startup_id}.json"
    tmp_file = cache_dir / f"{startup_id}.tmp.json"

    cached_evals: dict[str, dict[str, Any]] = {}
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_evals = {item["q_id"]: item for item in json.load(f)}
            logger.info(f"Found existing cache for {startup_id} with {len(cached_evals)} questions")
        except Exception as e:
            logger.warning(f"Error reading existing cache: {e}")

    remaining_questions = [q for q in rubric if (q.get("new_q_id", q.get("q_id")) not in cached_evals)]
    if not remaining_questions:
        logger.info(f"Startup {startup_id} already fully evaluated ({len(cached_evals)} questions).")
        return {"startup_id": startup_id, "total": len(cached_evals), "cache_file": str(cache_file)}

    logger.info(f"Processing {len(remaining_questions)} remaining questions with concurrency={concurrency} (batch_size={batch_size})...")

    if model_id is None:
        if _is_ollama(sglang_url):
            raise ValueError(
                "Pass --model when the endpoint is Ollama. The first listed model is not the scorer."
            )
        model_id = get_active_model_id(sglang_url)
    logger.info(f"Connected to model serving: {model_id}")
    try:
        inst_client = create_instructor_client(sglang_url, timeout=60)
    except Exception as e:
        logger.warning(f"Could not initialize Instructor client: {e}; falling back to direct mode")
        inst_client = None

    completed_count = 0
    total_to_run = len(remaining_questions)

    if batch_size <= 1:
        def _score_one(q: dict[str, Any]) -> dict[str, Any]:
            return score_question(
                q,
                category_contexts.get(q.get("cat_code") or "") or {},
                query_fn=query_sglang_question,
                client=inst_client,
                model_id=model_id,
                timeout=timeout,
                doc_manifest=doc_manifest,
                endpoint=sglang_url,
                startup_id=startup_id,
            )

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_q = {executor.submit(_score_one, q): q for q in remaining_questions}

            for future in as_completed(future_to_q):
                q = future_to_q[future]
                qid = q.get("new_q_id", q.get("q_id"))
                try:
                    eval_record = future.result()
                except Exception as e:
                    logger.error(f"Execution error on {qid}: {e}")
                    eval_record = _withhold(qid, [{"check": "timeout", "detail": str(e)}], error_code="TIMEOUT")

                cached_evals[qid] = eval_record
                completed_count += 1

                if completed_count % 10 == 0 or completed_count == total_to_run:
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        json.dump(list(cached_evals.values()), f, indent=2)
                    os.replace(tmp_file, cache_file)
                    logger.info(
                        f"Progress [{completed_count}/{total_to_run}] | Latest {qid}: "
                        f"Score={eval_record['predicted_val']} | Cit={bool(eval_record['citation'])}"
                    )
    else:
        # Batching path: first short-circuit deterministic criteria
        questions_to_batch: list[dict[str, Any]] = []
        for q in remaining_questions:
            cat = q.get("cat_code") or ""
            ctx = category_contexts.get(cat) or {}
            primary_text = ctx.get("primary_text", "")
            if ctx.get("has_primary", False):
                det = deterministic_answer(q, primary_text, startup_id)
                if det is not None:
                    qid = q.get("new_q_id", q.get("q_id"))
                    cached_evals[qid] = det
                    completed_count += 1
                    continue
            questions_to_batch.append(q)

        groups = group_questions(questions_to_batch, batch_size)

        def _score_group(grp: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
            if not grp:
                return []
            cat = grp[0].get("cat_code") or ""
            ctx = category_contexts.get(cat) or {}
            primary_text = ctx.get("primary_text", "")
            has_primary = ctx.get("has_primary", False)

            raw_items = query_batch(
                inst_client,
                model_id,
                ctx.get("text", ""),
                grp,
                timeout,
                doc_manifest,
                has_primary,
                sglang_url,
                startup_id=startup_id,
                temperature=0.0,
            )

            results = []
            for q, raw in zip(grp, raw_items):
                rec = accept_model_answer(raw, primary_text, q, company=startup_id)
                if rec.get("error_code") == "TIMEOUT" or rec.get("error_code") in RETRYABLE_ERROR_CODES:
                    rec = score_question(
                        q,
                        ctx,
                        query_fn=query_sglang_question,
                        client=inst_client,
                        model_id=model_id,
                        timeout=timeout,
                        doc_manifest=doc_manifest,
                        endpoint=sglang_url,
                        startup_id=startup_id,
                    )
                results.append((q, rec))
            return results

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_grp = {executor.submit(_score_group, grp): grp for grp in groups}
            for future in as_completed(future_to_grp):
                grp = future_to_grp[future]
                try:
                    pairs = future.result()
                except Exception as e:
                    logger.error(f"Execution error on batch group: {e}")
                    pairs = [
                        (q, _withhold(q.get("new_q_id", q.get("q_id")), [{"check": "timeout", "detail": str(e)}], error_code="TIMEOUT"))
                        for q in grp
                    ]
                for q, eval_record in pairs:
                    qid = q.get("new_q_id", q.get("q_id"))
                    cached_evals[qid] = eval_record
                    completed_count += 1
                    if completed_count % 10 == 0 or completed_count == total_to_run:
                        with open(tmp_file, "w", encoding="utf-8") as f:
                            json.dump(list(cached_evals.values()), f, indent=2)
                        os.replace(tmp_file, cache_file)
                        logger.info(
                            f"Progress [{completed_count}/{total_to_run}] | Latest {qid}: "
                            f"Score={eval_record['predicted_val']} | Cit={bool(eval_record['citation'])}"
                        )

    elapsed = time.time() - start_time
    citations_count = sum(1 for e in cached_evals.values() if e.get("citation"))
    scored_count = sum(1 for e in cached_evals.values() if e.get("predicted_val") is not None)

    logger.info(
        f"Completed {startup_id} in {elapsed:.2f}s | "
        f"Total Questions: {len(cached_evals)} | "
        f"Scored: {scored_count} | Citations: {citations_count}"
    )

    primary_map_path = cache_dir / f"{startup_id}.primary_map.json"
    primary_map_path.write_text(
        json.dumps(
            {cat: ctx.get("primary_text", "") for cat, ctx in category_contexts.items()},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "startup_id": startup_id,
        "elapsed_sec": elapsed,
        "total_questions": len(cached_evals),
        "scored_count": scored_count,
        "citations_count": citations_count,
        "cache_file": str(cache_file),
        "primary_map_file": str(primary_map_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parsed-markdown diligence extractor (no PDF provenance)")
    parser.add_argument("--startup", default="17", help="Startup ID to evaluate (e.g. 17 or ALL)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to evaluate")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent worker threads")
    parser.add_argument("--sglang-url", default=DEFAULT_SGLANG_URL, help="Model server base URL")
    parser.add_argument("--parsed-dir", default=DEFAULT_PARSED_DIR, help="parsed_clean_v4 base directory")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Output cache directory (ai_cache_v5_parsed)")
    parser.add_argument("--rubric", default=DEFAULT_RUBRIC_PATH, help="Rubric JSON file path")
    parser.add_argument("--model", default=None, help="Model id. Required for an Ollama endpoint.")
    parser.add_argument("--question-ids", default=None, help="Comma-separated question ids to score")
    parser.add_argument("--allowlist", default=None, help="Active startup allowlist JSON")
    parser.add_argument("--batch-size", type=int, default=1, help="Same-category batch size (default 1)")
    args = parser.parse_args()

    allow_ids, allow_path = load_active_allowlist(args.allowlist)
    allow_set = set(allow_ids)
    logger.info("Allowlist %s: %d startups", allow_path, len(allow_ids))
    os.makedirs(args.cache_dir, exist_ok=True)

    common = dict(
        sglang_url=args.sglang_url,
        rubric_path=args.rubric,
        parsed_base_dir=args.parsed_dir,
        cache_base_dir=args.cache_dir,
        limit=args.limit,
        concurrency=args.concurrency,
        model_id=args.model,
        question_ids=args.question_ids.split(",") if args.question_ids else None,
        batch_size=args.batch_size,
    )

    if args.startup == "ALL":
        missing = [s for s in allow_ids if not (Path(args.parsed_dir) / s).is_dir()]
        if missing:
            raise SystemExit(
                f"{len(missing)} allowlisted startups have no parsed directory under {args.parsed_dir}: {missing}"
            )
        logger.info(f"Running parsed-markdown extraction on {len(allow_ids)} allowlisted startups...")
        for s in allow_ids:
            try:
                evaluate_startup(startup_id=s, **common)
            except Exception as e:
                logger.error(f"Error processing {s}: {e}")
    else:
        if args.startup not in allow_set:
            raise SystemExit(
                f"{args.startup} is not on the active allowlist ({allow_path}). "
                "Disk-only folders such as SPARK and tmp_pages are excluded."
            )
        evaluate_startup(startup_id=args.startup, **common)
