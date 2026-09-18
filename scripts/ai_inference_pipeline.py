#!/usr/bin/env python3
"""
CleanTech Open Production AI Backfill Engine (Detached Spark Execution)
======================================================================
Targets ONLY ambiguous compound/partial gates (coded as -1).
Preserves legacy missing data (coded as NULL) for historical fidelity.

Pipeline Flow:
1. Discovers startups with ambiguous_count > 0.
2. Extracts document text from /data/cleantech/data/raw/ via PyMuPDF (fitz) and BeautifulSoup.
   Implements category-specific document targeting to avoid context saturation.
3. Batches ambiguous questions to local Ollama (llama3.2:latest).
4. Records verbatim citations and confidence to JSON checkpoints and cleantech.evaluation_evidence.
5. Updates cleantech.startup_scores_363 (converting -1 to 1 or 0) and refreshes rollups.
"""

import os
import sys
import re
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd
import requests

try:
    import fitz
    from bs4 import BeautifulSoup
except ImportError:
    pass

OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "llama3.2:latest"
RAW_DATA_BASE = Path("/data/cleantech/data/raw")
EXPORT_DIR = Path("/home/jkim/data/processed/postgres_export")
EVIDENCE_DIR = Path("/home/jkim/data/processed/backfilled_evidence")


def normalize_company_name(s: str) -> str:
    """Strips legal entities and punctuation for high-yield directory matching."""
    s = str(s).lower()
    # Replace common separators with space to ensure word boundaries work
    s = re.sub(r'[\_\-\,\.]', ' ', s)
    # Remove common corporate suffixes
    suffixes = [r'\binc\b', r'\bllc\b', r'\bcorp\b', r'\bcorporation\b', r'\btechnologies\b', r'\bsolutions\b', r'\bsystems\b']
    for suffix in suffixes:
        s = re.sub(suffix, '', s)
    # Remove all non-alphanumeric characters
    return re.sub(r"[^a-z0-9]", "", s)


def extract_startup_text(company_name: str, category_code: str, raw_base: Path = RAW_DATA_BASE) -> str:
    """Finds startup directory and extracts text from targeted PDFs based on category."""
    c_target = normalize_company_name(company_name)
    matched_dir = None

    if raw_base.exists():
        for d in raw_base.iterdir():
            if d.is_dir() and normalize_company_name(d.name) == c_target:
                matched_dir = d
                break

    if not matched_dir or not matched_dir.exists():
        return ""

    # Category-specific file filters and token (word) caps
    filters = []
    word_cap = 4000

    if category_code == "BC":
        filters = ["*_BMC.pdf", "*master.html"]
        word_cap = 4000
    elif category_code == "F":
        filters = ["*Financial*.pdf", "*ProForma*.pdf", "*Budget*.pdf"]
        word_cap = 4000
    elif category_code == "IP":
        filters = ["*Pitch*.pdf", "*Deck*.pdf", "*Presentation*.pdf"]
        word_cap = 5000
    elif category_code == "T":
        filters = ["*Team*.pdf", "*master.html"]
        word_cap = 3000
    elif category_code == "IS":
        filters = ["*Impact*.pdf", "*Sustainability*.pdf", "*SDG*.pdf"]
        word_cap = 3000
    elif category_code in ["TP", "PMF", "M"]:
        filters = ["*Archetype*.pdf", "*Competitive*.pdf", "*TRL*.pdf"]
        word_cap = 4000
    else:
        filters = ["*_master.html"]
        word_cap = 4000

    text_parts = []
    
    # 1. Match targeted PDFs and HTMLs
    matched_files = []
    for f_pattern in filters:
        for file_path in matched_dir.rglob(f_pattern):
            if file_path not in matched_files:
                matched_files.append(file_path)

    # 2. If no files matched, fallback to *master.html
    if not matched_files:
        for file_path in matched_dir.rglob("*_master.html"):
            if file_path not in matched_files:
                matched_files.append(file_path)

    for file_path in matched_files:
        try:
            if file_path.suffix.lower() == ".html":
                soup = BeautifulSoup(file_path.read_text(errors="ignore"), "html.parser")
                txt = soup.get_text()
                txt = re.sub(r"\s+", " ", txt).strip()
                if txt:
                    text_parts.append(f"--- APPLICATION FORM ({file_path.name}) ---\n" + txt)
            elif file_path.suffix.lower() == ".pdf":
                doc = fitz.open(file_path)
                pdf_text = []
                for page_idx, page in enumerate(doc):
                    ptxt = page.get_text()
                    if ptxt.strip():
                        pdf_text.append(f"[Page {page_idx+1}] {ptxt.strip()}")
                if pdf_text:
                    full_pdf = "\n".join(pdf_text)
                    text_parts.append(f"--- DOCUMENT ({file_path.name}) ---\n" + full_pdf)
        except Exception:
            pass

    full_text = "\n\n".join(text_parts)
    # Truncate by word count approximately (splitting by whitespace)
    words = full_text.split()
    if len(words) > word_cap:
        words = words[:word_cap]
    return " ".join(words)


def extract_json_from_markdown(text: str) -> dict:
    """Robustly extracts JSON from markdown or raw text output."""
    # Try to find markdown JSON block
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Fallback: find any JSON-like structure
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
            
    return {}


def evaluate_questions_batch(startup_text: str, questions: list[dict]) -> list[dict]:
    """Queries Llama3.2 via Ollama for a batch of ambiguous questions.
    
    Prompt constraints:
    - Enumerates the exact allowed question_id values.
    - Mandates exactly len(questions) objects in the output array.
    - Post-filters results to reject any response with a hallucinated/drifted question_id.
    """
    allowed_ids = [q["question_id"] for q in questions]
    n = len(questions)

    # Build the criteria block, numbering each item for model clarity
    q_lines = []
    for i, q in enumerate(questions, start=1):
        q_lines.append(f"{i}. question_id MUST be \"{q['question_id']}\" | Criteria: {q['text']}")
    q_str = "\n".join(q_lines)

    allowed_ids_str = ", ".join(f'"{qid}"' for qid in allowed_ids)

    prompt = f"""You are an expert venture capital analyst and document auditor conducting a structured due-diligence review.

Your task: evaluate EXACTLY {n} binary criteria against the startup document excerpts below.

RULES — read carefully before responding:
1. You MUST return a JSON object with an "evaluations" array containing EXACTLY {n} items — one per criterion listed.
2. Each item's "question_id" field MUST be copied VERBATIM from the list. Allowed values: [{allowed_ids_str}]. Do NOT paraphrase, rename, or invent IDs.
3. "binary_score" MUST be the integer 1 (criterion satisfied) or 0 (criterion not satisfied). Do NOT use null, strings, or floats.
4. "confidence" MUST be a float between 0.00 and 1.00 reflecting your certainty.
5. "citation" MUST be a direct verbatim quote (max 200 chars) from the document that supports your decision. If no evidence exists, write "No evidence found." and set binary_score to 0.
6. "page_number" MUST be the page number of the citation (integer). Use 1 if not determinable.
7. Do NOT add commentary, preamble, or text outside the JSON block.

DOCUMENT EXCERPTS:
\"\"\"
{startup_text}
\"\"\"

CRITERIA TO EVALUATE ({n} items — respond to ALL):
{q_str}

Respond with ONLY the following JSON block — nothing before or after it:
```json
{{
  "evaluations": [
    {{
      "question_id": "<VERBATIM_ID_FROM_LIST>",
      "binary_score": 0,
      "confidence": 0.00,
      "citation": "<VERBATIM_QUOTE_OR_No evidence found.>",
      "page_number": 1
    }}
  ]
}}
```"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 2048
        }
    }

    try:
        r = requests.post(OLLAMA_API_URL, json=payload, timeout=90)
        r.raise_for_status()
        raw_resp = r.json().get("response", "{}")

        data = extract_json_from_markdown(raw_resp)

        evals = data.get("evaluations", [])
        if not evals and isinstance(data, list):
            evals = data
        elif not evals and isinstance(data, dict) and "question_id" in data:
            evals = [data]

        # --- Post-validation: reject any result whose question_id is not in the allowed set ---
        allowed_set = set(allowed_ids)
        valid_evals = []
        for ev in evals:
            qid = ev.get("question_id")
            score = ev.get("binary_score")
            if qid in allowed_set and score in (0, 1):
                valid_evals.append(ev)
            else:
                print(f"      [WARN] Dropped invalid response: question_id='{qid}', binary_score='{score}'")

        return valid_evals

    except Exception as e:
        print(f"      [WARN] Inference error: {e}")
        return []



def update_database_results(startup_id: str, results: list[dict]):
    """Applies resolved scores and inserts evidence into PostgreSQL."""
    if not results:
        return

    sql_statements = ["SET search_path TO cleantech, public;"]
    
    # 1. Update startup_scores_363 columns
    set_clauses = []
    for res in results:
        qid = res.get("question_id")
        score = res.get("binary_score")
        if qid and score in (0, 1):
            set_clauses.append(f"{qid} = {score}")

    if set_clauses:
        sql_statements.append(f"""
        UPDATE cleantech.startup_scores_363
        SET {', '.join(set_clauses)},
            updated_at = CURRENT_TIMESTAMP
        WHERE startup_id = '{startup_id}';
        """)

    # 2. Insert into evaluation_evidence
    for res in results:
        qid = res.get("question_id")
        score = res.get("binary_score")
        conf = float(res.get("confidence") or 0.80)
        citation = str(res.get("citation") or "No citation provided.").replace("'", "''")[:1000]
        page = int(res.get("page_number") or 1)

        if qid and score in (0, 1):
            sql_statements.append(f"""
            INSERT INTO cleantech.evaluation_evidence 
                (startup_id, question_id, binary_score, confidence, citation_text, page_number, evaluator_role, model_or_user)
            VALUES 
                ('{startup_id}', '{qid}', {score}, {conf:.2f}, '{citation}', {page}, 'AI', '{MODEL_NAME}')
            ON CONFLICT (startup_id, question_id) 
            DO UPDATE SET 
                binary_score = EXCLUDED.binary_score,
                confidence = EXCLUDED.confidence,
                citation_text = EXCLUDED.citation_text,
                page_number = EXCLUDED.page_number,
                evaluated_at = CURRENT_TIMESTAMP;
            """)

    # Execute batch in psql
    full_sql = "\n".join(sql_statements)
    subprocess.run(
        ["psql", "-U", "jkim", "-d", "sec_data", "-c", full_sql],
        capture_output=True,
        text=True
    )


def recalculate_startup_rollups():
    """Recalculates summary rollup metrics across all startups in PostgreSQL."""
    update_sql = """
    SET search_path TO cleantech, public;
    
    WITH summary_calc AS (
        SELECT 
            sc.startup_id,
            COUNT(CASE WHEN val = '1' THEN 1 END) AS new_binary_passed,
            COUNT(CASE WHEN val IN ('0', '1') THEN 1 END) AS new_resolved,
            COUNT(CASE WHEN val = '-1' THEN 1 END) AS new_ambiguous,
            COUNT(CASE WHEN val IS NULL THEN 1 END) AS new_missing
        FROM cleantech.startup_scores_363 sc,
        LATERAL jsonb_each_text(to_jsonb(sc) - '{startup_id,total_binary_passed,ai_auto_passed,human_verified_passed,total_score_pct,resolved_count,ambiguous_count,missing_legacy_count,updated_at}'::text[]) q(key, val)
        GROUP BY sc.startup_id
    )
    UPDATE cleantech.startup_scores_363 sc
    SET 
        total_binary_passed = s.new_binary_passed,
        resolved_count = s.new_resolved,
        ambiguous_count = s.new_ambiguous,
        missing_legacy_count = s.new_missing,
        total_score_pct = ROUND((s.new_binary_passed::numeric / 357.0) * 100.0, 2),
        updated_at = CURRENT_TIMESTAMP
    FROM summary_calc s
    WHERE sc.startup_id = s.startup_id;
    """
    subprocess.run(["psql", "-U", "jkim", "-d", "sec_data", "-c", update_sql], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="CleanTech Open Production AI Backfill Engine")
    parser.add_argument("--batch-size", type=int, default=3, help="Number of questions per LLM prompt (default: 3 for optimal logic retention)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of startups to process")
    args = parser.parse_args()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    print("====================================================================")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launching Detached AI Backfill Engine")
    print(f"Model:       {MODEL_NAME}")
    print(f"Database:    sec_data (schema: cleantech)")
    print(f"Target:      Ambiguous (-1) gates only (Legacy NULL preserved)")
    print("====================================================================")

    # 1. Query queue from PostgreSQL
    psql_cmd = """
    COPY (
        SELECT startup_id, company_name, cohort_year, question_id, cat_code, question_text
        FROM cleantech.v_ai_backfill_queue
        ORDER BY cohort_year DESC, startup_id, cat_code, question_id
    ) TO STDOUT WITH (FORMAT csv, HEADER true);
    """
    res = subprocess.run(
        ["psql", "-U", "jkim", "-d", "sec_data", "-c", psql_cmd],
        capture_output=True,
        text=True,
        check=True
    )
    
    from io import StringIO
    queue_df = pd.read_csv(StringIO(res.stdout))
    total_queue_items = len(queue_df)
    unique_startups = queue_df["startup_id"].unique()

    print(f"Queue Status: {total_queue_items:,} ambiguous gates across {len(unique_startups)} startups.")

    if args.limit:
        unique_startups = unique_startups[:args.limit]
        print(f"Limiting execution to first {len(unique_startups)} startups.")

    completed_count = 0
    total_gates_resolved = 0
    start_time = time.time()

    for idx, sid in enumerate(unique_startups):
        checkpoint_file = EVIDENCE_DIR / f"{sid}_evidence.json"
        if checkpoint_file.exists():
            print(f"[{idx+1}/{len(unique_startups)}] Skipping {sid} (already completed in checkpoints).")
            continue

        s_rows = queue_df[queue_df["startup_id"] == sid]
        comp_name = s_rows["company_name"].iloc[0]
        year = s_rows["cohort_year"].iloc[0]
        
        print(f"\n[{idx+1}/{len(unique_startups)}] {comp_name} ({year}) | {len(s_rows)} ambiguous gates")

        startup_results = []
        
        # Group by category code so we can fetch category-specific context
        for cat_code, cat_group in s_rows.groupby("cat_code"):
            q_list = cat_group[["question_id", "question_text"]].rename(columns={"question_text": "text"}).to_dict("records")
            
            # Extract category-specific document text
            doc_text = extract_startup_text(comp_name, cat_code)
            if not doc_text:
                print(f"      [SKIP] No relevant documents found for {comp_name} (Category: {cat_code}).")
                continue

            print(f"      [{cat_code}] Extracted {len(doc_text.split()):,} words for {len(q_list)} gates")

            # Batch evaluation for this category
            for i in range(0, len(q_list), args.batch_size):
                batch = q_list[i:i + args.batch_size]
                b_res = evaluate_questions_batch(doc_text, batch)
                startup_results.extend(b_res)
                print(f"      -> [{cat_code}] Evaluated batch {i//args.batch_size + 1}/{(len(q_list)-1)//args.batch_size + 1}: {len(b_res)}/{len(batch)} gates")

        # Save checkpoint
        if startup_results:
            with open(checkpoint_file, "w") as f:
                json.dump({
                    "startup_id": sid,
                    "company_name": comp_name,
                    "cohort_year": int(year),
                    "evaluated_at": datetime.now().isoformat(),
                    "results": startup_results
                }, f, indent=2)

            # Update PostgreSQL live
            update_database_results(sid, startup_results)
            total_gates_resolved += len(startup_results)
            completed_count += 1

            # Recalculate rollups every 5 startups
            if completed_count % 5 == 0:
                recalculate_startup_rollups()
                elapsed = time.time() - start_time
                print(f"      [PROGRESS] {completed_count} startups completed | {total_gates_resolved} gates resolved | Elapsed: {elapsed/60:.1f} min")

    # Final summary refresh
    recalculate_startup_rollups()
    total_elapsed = time.time() - start_time
    print("\n====================================================================")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AI Backfill Run Completed!")
    print(f"Total Startups Processed: {completed_count}")
    print(f"Total Gates Resolved:     {total_gates_resolved}")
    print(f"Total Run Time:           {total_elapsed/60:.1f} minutes")
    print("====================================================================")


if __name__ == "__main__":
    main()
