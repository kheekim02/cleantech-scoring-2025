import json
import os
import time
import requests
import sys

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'deepseek-coder-v2:16b'
RUBRIC_PATH = '/tmp/master_363_rubric.json'
RAW_BASE_DIR = '/data/scraping/datasets/cto_accelerator/parsed'
CACHE_DIR = '/data/scraping/datasets/cto_accelerator/ai_cache_363'

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)

with open(RUBRIC_PATH, 'r') as f:
    rubric = json.load(f)

consecutive_failures = 0

def extract_single_question(q, doc_text):
    global consecutive_failures
    q_id = q.get('new_q_id', q.get('q_id'))
    q_simple = {
        'q_id': q_id,
        'text': q['text'],
        'options': [o['val'] for o in q['options']]
    }
    
    prompt = f"""You are a strict startup evaluator. Read the document and evaluate this single criteria.
Output a valid JSON object. Do NOT wrap in markdown.

<document>
{doc_text[:8000]}
</document>

<question>
{json.dumps(q_simple, indent=2)}
</question>

Output exactly one JSON object with these keys:
"q_id": the question ID
"predicted_val": exactly 1 (if YES/True) or 0 (if NO/False)
"confidence": float between 0.0 and 1.0
"citation": exact verbatim quote from the document supporting the answer (or null if not found)
"""
    
    for attempt in range(3):
        try:
            resp = requests.post(OLLAMA_URL, json={
                'model': MODEL, 'prompt': prompt, 'stream': False, 
                'options': {'temperature': 0.0, 'num_predict': 500}
            }, timeout=300)
            
            if resp.status_code == 200:
                data = resp.json()
                raw = data.get('response', '').strip()
                if '```json' in raw: raw = raw.split('```json')[1].split('```')[0].strip()
                elif '```' in raw: raw = raw.split('```')[1].split('```')[0].strip()
                
                parsed = json.loads(raw)
                if isinstance(parsed, list) and len(parsed) > 0: parsed = parsed[0]
                
                if isinstance(parsed, dict) and 'q_id' in parsed:
                    cit = parsed.get('citation')
                    if cit and isinstance(cit, str) and cit not in doc_text:
                        print(f"  [!] Hallucinated citation for {q_id}. Rejecting.")
                        return "HALLUCINATED"
                        
                    consecutive_failures = 0
                    return parsed
                    
        except Exception as e:
            pass
            
        time.sleep(5)
        
    consecutive_failures += 1
    if consecutive_failures >= 10:
        print("[CRITICAL] Circuit breaker triggered: 10 consecutive LLM failures. Halting daemon.")
        sys.exit(1)
        
    return "FAILED"

def process_company(company, limit=None):
    cache_path = os.path.join(CACHE_DIR, f"{company}.json")
    tmp_path = f"{cache_path}.tmp"
    
    cache_results = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cache_results = {r['q_id']: r for r in json.load(f)}
        except:
            pass
            
    if len(cache_results) >= len(rubric):
        print(f"[{company}] Already complete. Skipping.")
        return
        
    cat_dir = os.path.join(RAW_BASE_DIR, company, 'converted')
    if not os.path.exists(cat_dir): return
        
    doc_text = ""
    for f in os.listdir(cat_dir):
        if f.endswith('.md'):
            with open(os.path.join(cat_dir, f), 'r', errors='ignore') as file:
                doc_text += file.read() + "\n\n"
                
    if not doc_text.strip(): return
    
    queue = []
    for q in rubric:
        q_id = q.get('new_q_id', q.get('q_id'))
        if q_id not in cache_results or cache_results[q_id].get('predicted_val') is None:
            queue.append({"q": q, "global_retries": 0})
            
    if limit:
        queue = queue[:limit]
            
    print(f"[{company}] Processing {len(queue)} remaining questions...")
    
    while queue:
        item = queue.pop(0)
        q = item['q']
        q_id = q.get('new_q_id', q.get('q_id'))
        
        start_time = time.time()
        res = extract_single_question(q, doc_text)
        duration = time.time() - start_time
        
        if res in ("HALLUCINATED", "FAILED"):
            item['global_retries'] += 1
            if item['global_retries'] < 3:
                queue.append(item)
                continue
            else:
                res = {'q_id': q_id, 'predicted_val': None, 'confidence': None, 'citation': None}
        
        cache_results[q_id] = res
        
        with open(tmp_path, 'w') as f:
            json.dump(list(cache_results.values()), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, cache_path)
        
        print(f"  -> {q_id} completed successfully in {duration:.2f}s ({len(cache_results)}/{len(rubric)})")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        process_company('Condor_Calibration_Services', limit=3)
        sys.exit(0)
        
    companies = os.listdir(RAW_BASE_DIR)
    companies = [c for c in companies if c != 'spark_inc' and c != 'solarpure_inc' and not c.startswith('startup_test_')]
    for c in sorted(companies):
        process_company(c)
    print("ALL COMPANIES PROCESSED.")
