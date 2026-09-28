"""High-Throughput Grounded Diligence Extractor v2 (SGLang + Docling + Instructor).

Evaluates clean startup applications against the standardized 282-criteria rubric using:
- RadixAttention prefix caching on Spark GB10 for near-zero TTFT across all questions
- Concurrent asynchronous batch dispatching
- Instructor / Pydantic v2 schemas enforcing 0.0 - 1.0 scoring
- Verbatim citation grounding with bounding-box and page provenance resolution
"""
import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import instructor
from openai import OpenAI

from src.scorer.schemas import (
    QuestionEvaluation,
    RawModelExtraction,
    match_citation_to_chunks,
    is_negative_citation,
)
from scripts.docling_ingestion import process_startup_folder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extractor_v2")

DEFAULT_SGLANG_URL = os.environ.get("SGLANG_BASE_URL", "http://127.0.0.1:30000")
DEFAULT_RUBRIC_PATH = "master_282_rubric.json"
REMOTE_DATASET_ROOT = "/data/scraping/datasets/cto_accelerator"
# v4 chunks are classified with the current resolver. docling_clean only has
# 17 and 2DaLoop from before that resolver, so a rerun must not reuse it.
REMOTE_DOCLING_DIR = "/data/scraping/data/docling_clean_v4"
SHADOW_CACHE_NAME = "ai_cache_v4_shadow"
ALLOWLIST_NAME = "active_startup_allowlist.json"
DEFAULT_RAW_DIR = os.path.join(REMOTE_DATASET_ROOT, "raw")


def default_docling_dir() -> str:
    """Use a fresh server chunk cache when this process is on the dataset host."""
    if os.path.isdir(REMOTE_DATASET_ROOT):
        os.makedirs(REMOTE_DOCLING_DIR, exist_ok=True)
        return REMOTE_DOCLING_DIR
    return "data/docling_clean_v4"


def default_cache_dir() -> str:
    """Write the next generation beside v3_strict, never into archived caches."""
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


def get_active_model_id(sglang_url: str) -> str:
    """Fetch active model ID from SGLang /v1/models."""
    url = f"{sglang_url}/v1/models"
    req = urllib.request.Request(url, headers={"User-Agent": "CTO-Extractor/2.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        return data["data"][0]["id"]


def create_instructor_client(sglang_url: str, timeout: int = 60) -> Any:
    """Create Instructor client wrapping OpenAI client pointing to SGLang."""
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
# one-page executive summary is primary. Secondary documents stay in the prompt
# only after the primary text, inside the character cap.
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
CONTEXT_CHAR_LIMIT = 300_000

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


def _render_document(file_chunks: list[dict[str, Any]], role: str) -> str:
    fname = file_chunks[0].get("source_pdf") or "unknown"
    doc_type = file_chunks[0].get("doc_type", "OTHER")
    parts = [f"=== DOCUMENT: {fname} [Type: {doc_type}] [Role: {role}] ==="]
    for chunk in file_chunks:
        page = chunk.get("page_no") or chunk.get("page_number")
        page_info = f"[Page {page}] " if page else ""
        parts.append(f"{page_info}{chunk.get('text', '')}".strip())
    return "\n\n".join(parts)


def build_category_context(
    chunks: list[dict[str, Any]],
    cat_code: str,
    char_limit: int = CONTEXT_CHAR_LIMIT,
) -> dict[str, Any]:
    """Place primary deliverables first and keep them inside the character cap.

    Secondary documents fill only the remaining budget. A category with no
    classified primary file is not scored from the rest of the packet.
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
    secondary_files = [fname for fname in order if fname not in primary_files]
    pieces: list[str] = []
    used = 0

    def add_file(fname: str, role: str) -> bool:
        nonlocal used
        if used >= char_limit:
            return False
        block = _render_document(by_file[fname], role)
        remain = char_limit - used
        if len(block) > remain:
            block = block[:remain]
        pieces.append(block)
        used += len(block) + 3
        return used < char_limit

    for fname in primary_files:
        if not add_file(fname, "PRIMARY"):
            break
    if primary_files:
        for fname in secondary_files:
            if not add_file(fname, "SECONDARY"):
                break

    return {
        "text": "\n\n\n".join(pieces),
        "has_primary": bool(primary_files),
        "primary_filenames": primary_files,
    }


def query_sglang_question(
    client: Any,
    model_id: str,
    prefix_context: str,
    question: dict[str, Any],
    timeout: int = 60,
    doc_manifest: dict[str, list[str]] | None = None,
    has_primary: bool = True,
) -> dict[str, Any]:
    """Execute evaluation for a single rubric question against the cached prefix context using Instructor."""
    qid = question.get("new_q_id", question.get("q_id"))
    options = [o.get("val") for o in question.get("options", [])]
    options_desc = ", ".join(str(o) for o in options) if options else "0.0, 1.0"

    cat_code = question.get('cat_code', 'GENERAL')
    if not has_primary:
        return {
            "q_id": qid,
            "predicted_val": None,
            "confidence": 0.0,
            "citation": None,
            "rationale": "No primary source document was classified for this category.",
            "duration_sec": 0.0,
        }

    primary_filenames: list[str] = []
    if doc_manifest and cat_code in CAT_PRIMARY_SOURCES:
        for tc in CAT_PRIMARY_SOURCES[cat_code]:
            primary_filenames.extend(doc_manifest.get(tc, []))
    file_list = ", ".join(f'"{f}"' for f in primary_filenames) if primary_filenames else "the documents marked [Role: PRIMARY]"
    sourcing_instruction = (
        f"For this {cat_code} criterion, your PRIMARY source document(s) are: {file_list}. "
        f"Extract your citation from documents marked [Role: PRIMARY]. "
        f"Documents marked [Role: SECONDARY] may be used only when the primary documents contain no relevant evidence."
    )

    system_prompt = (
        "You are an objective due diligence evaluator scoring cleantech startup applications. "
        "Strictly adhere to the provided rubric and only quote verbatim text written by founders. "
        "Do NOT quote instructions or template boilerplate. "
        f"{sourcing_instruction}"
    )

    # Category context is already primary-first and capped. This slice is a backstop.
    safe_context = prefix_context[:CONTEXT_CHAR_LIMIT] if len(prefix_context) > CONTEXT_CHAR_LIMIT else prefix_context
    user_prompt = (
        f"<applicant_prose>\n{safe_context}\n</applicant_prose>\n\n"
        f"<rubric_criterion>\n"
        f"ID: {qid}\n"
        f"Category: {question.get('cat_code', 'GENERAL')}\n"
        f"Text: {question.get('text', '')}\n"
        f"Allowed Scoring Options: [{options_desc}]\n"
        f"</rubric_criterion>\n\n"
        f"Output ONLY a valid JSON object matching this schema:\n"
        f"{{\n"
        f'  "q_id": "{qid}",\n'
        f'  "predicted_val": <one number chosen strictly from Allowed Scoring Options, or null if no evidence>,\n'
        f'  "confidence": <float 0.0 to 1.0>,\n'
        f'  "citation": <exact 1-2 sentence verbatim quote from applicant_prose providing proof, or null if no evidence>,\n'
        f'  "rationale": <brief 1-sentence explanation of score>\n'
        f"}}"
    )

    t0 = time.perf_counter()
    if client is not None:
        try:
            extraction: RawModelExtraction = client.chat.completions.create(
                model=model_id,
                response_model=RawModelExtraction,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
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
        "temperature": 0.0,
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
        "rationale": "Evaluation failed or timed out",
        "duration_sec": round(time.perf_counter() - t0, 3),
    }



def evaluate_startup(
    startup_id: str,
    sglang_url: str = DEFAULT_SGLANG_URL,
    rubric_path: str = DEFAULT_RUBRIC_PATH,
    chunks_base_dir: str = DEFAULT_DOCLING_DIR,
    cache_base_dir: str = DEFAULT_CACHE_DIR,
    raw_base_dir: str = DEFAULT_RAW_DIR,
    catalog_path: str | None = None,
    limit: int | None = None,
    concurrency: int = 10,
) -> dict[str, Any]:
    """Execute complete 282-question diligence extraction for a single startup."""
    start_time = time.time()
    logger.info(f"=== Evaluating Startup: {startup_id} ===")

    # 1. Ensure Docling chunks and full text markdown exist
    startup_docling_dir = Path(chunks_base_dir) / startup_id
    chunks_file = startup_docling_dir / "chunks.json"
    full_text_file = startup_docling_dir / "full_text.md"

    if not chunks_file.exists() or not full_text_file.exists():
        startup_raw_dir = Path(raw_base_dir) / startup_id
        if not startup_raw_dir.exists():
            raise FileNotFoundError(f"Raw directory not found for {startup_id} at {startup_raw_dir}")
        logger.info(f"Ingesting documents via Docling for {startup_id}...")
        process_startup_folder(str(startup_raw_dir), str(startup_docling_dir), catalog_path=catalog_path)

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    with open(full_text_file, "r", encoding="utf-8") as f:
        prefix_context = f.read()

    # Build per-startup document manifest mapping doc_type -> actual filenames
    doc_manifest = build_doc_manifest(chunks)
    category_contexts = {
        cat: build_category_context(chunks, cat) for cat in CAT_PRIMARY_SOURCES
    }
    logger.info(
        f"Loaded {len(chunks)} chunks, full text size: {len(prefix_context):,} chars | "
        f"Document manifest: { {k: v for k, v in sorted(doc_manifest.items())} }"
    )
    for cat, ctx in category_contexts.items():
        logger.info(
            "Context %s primary=%s files=%s chars=%s",
            cat,
            ctx["has_primary"],
            ctx["primary_filenames"],
            len(ctx["text"]),
        )

    # 2. Load Rubric
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


    if limit:
        rubric = rubric[:limit]

    # 3. Load or initialize cache
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

    logger.info(f"Processing {len(remaining_questions)} remaining questions with concurrency={concurrency}...")

    # 4. Connect to SGLang and initialize Instructor
    model_id = get_active_model_id(sglang_url)
    logger.info(f"Connected to SGLang serving: {model_id}")
    try:
        inst_client = create_instructor_client(sglang_url, timeout=60)
    except Exception as e:
        logger.warning(f"Could not initialize Instructor client: {e}; falling back to direct mode")
        inst_client = None

    # 5. Concurrent Question Batch Execution
    completed_count = 0
    total_to_run = len(remaining_questions)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_q = {
            executor.submit(
                query_sglang_question,
                inst_client,
                model_id,
                category_contexts.get(q.get("cat_code") or "", {}).get("text", ""),
                q,
                60,
                doc_manifest,
                category_contexts.get(q.get("cat_code") or "", {}).get("has_primary", False),
            ): q for q in remaining_questions
        }

        for future in as_completed(future_to_q):
            q = future_to_q[future]
            qid = q.get("new_q_id", q.get("q_id"))
            try:
                raw_res = future.result()
            except Exception as e:
                logger.error(f"Execution error on {qid}: {e}")
                raw_res = {"q_id": qid, "predicted_val": None, "confidence": 0.0, "citation": None}

            # Grounding and Provenance Resolution
            citation = raw_res.get("citation")
            matched_provenance = match_citation_to_chunks(citation, chunks)

            if matched_provenance:
                source_pdf = matched_provenance.get("source_pdf")
                page_number = matched_provenance.get("page_number")
            else:
                source_pdf = None
                page_number = None
                # If citation failed grounding check, invalidate it
                citation = None

            # Build strictly validated QuestionEvaluation
            eval_record = QuestionEvaluation(
                q_id=qid,
                predicted_val=raw_res.get("predicted_val"),
                confidence=raw_res.get("confidence"),
                citation=citation,
                source_pdf=source_pdf,
                page_number=page_number,
                rationale=raw_res.get("rationale"),
            ).model_dump()

            cached_evals[qid] = eval_record
            completed_count += 1

            # Atomic save every 10 completions or at end
            if completed_count % 10 == 0 or completed_count == total_to_run:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(list(cached_evals.values()), f, indent=2)
                os.replace(tmp_file, cache_file)
                logger.info(f"Progress [{completed_count}/{total_to_run}] | Latest {qid}: Score={eval_record['predicted_val']} | Cit={bool(eval_record['citation'])}")

    elapsed = time.time() - start_time
    citations_count = sum(1 for e in cached_evals.values() if e.get("citation"))
    provenance_count = sum(1 for e in cached_evals.values() if e.get("page_number"))

    logger.info(
        f"Completed {startup_id} in {elapsed:.2f}s | "
        f"Total Questions: {len(cached_evals)} | "
        f"Citations Extracted: {citations_count} | "
        f"Page Provenance Mapped: {provenance_count} ({provenance_count/citations_count*100 if citations_count else 0:.1f}%)"
    )

    return {
        "startup_id": startup_id,
        "elapsed_sec": elapsed,
        "total_questions": len(cached_evals),
        "citations_count": citations_count,
        "provenance_count": provenance_count,
        "cache_file": str(cache_file),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="High-Throughput Grounded Diligence Extractor v2")
    parser.add_argument("--startup", default="17", help="Startup ID to evaluate (e.g. 17 or ALL)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to evaluate")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent worker threads")
    parser.add_argument("--sglang-url", default=DEFAULT_SGLANG_URL, help="SGLang server base URL")
    parser.add_argument("--chunks-dir", default=DEFAULT_DOCLING_DIR, help="Docling chunks base directory")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Output cache directory")
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR, help="Raw PDF base directory")
    parser.add_argument("--rubric", default=DEFAULT_RUBRIC_PATH, help="Rubric JSON file path")
    parser.add_argument("--catalog", default="data/scaffolding_master_catalog.json", help="Scaffolding catalog JSON")
    parser.add_argument("--allowlist", default=None, help="Active startup allowlist JSON")
    args = parser.parse_args()

    allow_ids, allow_path = load_active_allowlist(args.allowlist)
    allow_set = set(allow_ids)
    logger.info("Allowlist %s: %d startups", allow_path, len(allow_ids))
    os.makedirs(args.cache_dir, exist_ok=True)

    if args.startup == "ALL":
        raw_p = Path(args.raw_dir)
        missing = [s for s in allow_ids if not (raw_p / s).is_dir()]
        if missing:
            raise SystemExit(
                f"{len(missing)} allowlisted startups have no raw directory under {raw_p}: {missing}"
            )
        logger.info(f"Running v2 extraction on {len(allow_ids)} allowlisted startups...")
        for s in allow_ids:
            try:
                evaluate_startup(
                    startup_id=s,
                    sglang_url=args.sglang_url,
                    rubric_path=args.rubric,
                    chunks_base_dir=args.chunks_dir,
                    cache_base_dir=args.cache_dir,
                    raw_base_dir=args.raw_dir,
                    catalog_path=args.catalog,
                    limit=args.limit,
                    concurrency=args.concurrency,
                )
            except Exception as e:
                logger.error(f"Error processing {s}: {e}")
    else:
        if args.startup not in allow_set:
            raise SystemExit(
                f"{args.startup} is not on the active allowlist ({allow_path}). "
                "Disk-only folders such as SPARK and tmp_pages are excluded."
            )
        evaluate_startup(
            startup_id=args.startup,
            sglang_url=args.sglang_url,
            rubric_path=args.rubric,
            chunks_base_dir=args.chunks_dir,
            cache_base_dir=args.cache_dir,
            raw_base_dir=args.raw_dir,
            catalog_path=args.catalog,
            limit=args.limit,
            concurrency=args.concurrency,
        )
