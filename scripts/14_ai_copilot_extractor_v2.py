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
DEFAULT_CACHE_DIR = "data/ai_cache_v2"
DEFAULT_DOCLING_DIR = "data/docling_clean"
DEFAULT_RAW_DIR = "/data/scraping/datasets/cto_accelerator/raw"


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


def query_sglang_question(
    client: Any,
    model_id: str,
    prefix_context: str,
    question: dict[str, Any],
    timeout: int = 60,
) -> dict[str, Any]:
    """Execute evaluation for a single rubric question against the cached prefix context using Instructor."""
    qid = question.get("new_q_id", question.get("q_id"))
    options = [o.get("val") for o in question.get("options", [])]
    options_desc = ", ".join(str(o) for o in options) if options else "0.0, 1.0"

    system_prompt = (
        "You are an objective due diligence evaluator scoring cleantech startup applications. "
        "Strictly adhere to the provided rubric and only quote verbatim text written by founders. "
        "Do NOT quote instructions or template boilerplate."
    )

    # Cap prefix context to 300,000 chars (~75k tokens) to ensure rapid prefill within 131k window
    safe_context = prefix_context[:300000] if len(prefix_context) > 300000 else prefix_context
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

    logger.info(f"Loaded {len(chunks)} chunks, full text size: {len(prefix_context):,} chars")

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
                prefix_context,
                q
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
    args = parser.parse_args()

    if args.startup == "ALL":
        raw_p = Path(args.raw_dir)
        startups = [d.name for d in raw_p.iterdir() if d.is_dir() and not d.name.startswith(".")]
        logger.info(f"Running v2 extraction on {len(startups)} startups...")
        for s in sorted(startups):
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
