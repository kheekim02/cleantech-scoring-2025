import json
import os
import re
import requests
import concurrent.futures
from time import perf_counter
import psycopg2

DB_URL = "postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres?pgbouncer=true"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.6:35b"
CONFIDENCE_THRESHOLD = 0.85
BASE_DIR = "/Users/geoffrey/Global_Key_Advisors/Migrating_Automated_Startup_Scraper/data/parsed"
RUBRIC_PATH = "data/processed/scoring_interface_data.json"

with open(RUBRIC_PATH, "r") as f:
    rubric = json.load(f)["ai_by_cat"]

def extract_batch(cat_code, questions, document_text):
    q_text = "\n".join([f"- ID: {q['new_q_id']} | Text: {q['text']}" for q in questions])
    prompt = f"""You are a strict startup due diligence evaluator.
Read the document and evaluate the following criteria.
You MUST reply with a valid JSON array.

<document>
{document_text[:8000]}  # Limit context slightly to avoid context overflow
</document>

<questions>
{q_text}
</questions>

For each question, output a JSON object with:
"q_id": the exact question ID
"verdict": 1 for YES, 0 for NO
"confidence": float between 0.0 and 1.0
"citation": exact verbatim quote from the document supporting the answer (or null if not found)

Output ONLY a raw JSON array.
"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0}
        }, timeout=120)
        if resp.status_code == 200:
            return json.loads(resp.json()["response"])
    except Exception as e:
        print(f"Error on {cat_code}: {e}")
    return []

def process_company(company_name):
    cat_dir = os.path.join(BASE_DIR, company_name, "converted")
    if not os.path.exists(cat_dir): return
    
    print(f"\nProcessing {company_name}...")
    
    # Read all markdown files
    md_text = ""
    for f in os.listdir(cat_dir):
        if f.endswith(".md"):
            with open(os.path.join(cat_dir, f), "r", encoding="utf-8", errors="ignore") as file:
                md_text += file.read() + "\n\n"
                
    if not md_text.strip(): return
    
    # Send micro-batches concurrently
    batches = []
    for cat_code, qs in rubric.items():
        # Only evaluate categories that have binary questions
        binary_qs = [q for q in qs if q.get("type") == "BINARY"]
        for i in range(0, len(binary_qs), 5):
            batches.append((cat_code, binary_qs[i:i+5]))
            
    all_answers = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(extract_batch, b[0], b[1], md_text) for b in batches]
        for future in concurrent.futures.as_completed(futures):
            all_answers.extend(future.result())
            
    # Process into DB payload
    ai_cats = {}
    human_qs = []
    for cat_code, qs in rubric.items():
        ai_cats[cat_code] = {"questions": [], "passed": 0, "total": 0, "full_name": cat_code}
        
    for ans in all_answers:
        if not isinstance(ans, dict) or "q_id" not in ans: continue
        q_id = ans["q_id"]
        cat = q_id.split("_")[0] if "_" in q_id else ""
        if cat not in ai_cats: continue
        
        entry = {
            "new_q_id": q_id,
            "cat_code": cat,
            "verdict": ans.get("verdict", 0),
            "confidence": ans.get("confidence", 0.0),
            "verbatim_citation": ans.get("citation")
        }
        
        if entry["confidence"] >= CONFIDENCE_THRESHOLD:
            ai_cats[cat]["questions"].append(entry)
        else:
            entry["ai_suggestion"] = entry["verdict"]
            entry["ai_confidence"] = str(round(entry["confidence"], 2))
            human_qs.append(entry)
            
    # Commit
    payload = {
        "meta": {"id": company_name, "name": company_name.replace("_", " ")},
        "document": {"sections": []}, # We will wire PDFs later
        "ai_cats": ai_cats,
        "human_questions": human_qs
    }
    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO startup_extractions (startup_id, company_name, payload) VALUES (%s, %s, %s::jsonb) ON CONFLICT (startup_id) DO UPDATE SET payload = EXCLUDED.payload",
        (company_name, company_name.replace("_", " "), json.dumps(payload))
    )
    conn.commit()
    conn.close()
    print(f"Saved {company_name} to DB!")

if __name__ == "__main__":
    companies = [c for c in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, c))]
    print(f"Starting batch extraction for {len(companies)} companies...")
    for comp in companies:
        if comp not in ["SPARK", "converted"]: # skip already done
            process_company(comp)
