import json
import os
import sys
import time
import requests
import re

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'llama3.2:latest'
RUBRIC_PATH = '/data/scraping/datasets/cto_accelerator/master_282_rubric.json'
RAW_BASE_DIR = '/data/scraping/datasets/cto_accelerator/parsed_clean'
CACHE_DIR = '/data/scraping/datasets/cto_accelerator/ai_cache_clean'

os.makedirs(CACHE_DIR, exist_ok=True)

with open(RUBRIC_PATH, 'r') as f:
    rubric = json.load(f)

CAT_DOC_PATTERNS = {
    'BC': [r'Canvas', r'EBD3', r'M3'],
    'ES': [r'Executive_Summary', r'EBD1', r'Summary'],
    'IS': [r'EBD2', r'M2', r'GHG', r'Inclusion'],
    'M': [r'M4', r'EBD3', r'Customer'],
    'PMF': [r'M3', r'M1', r'CustomerDiscovery', r'Canvas'],
    'TP': [r'EBD4', r'TechnologyValidation', r'Patent'],
    'F': [r'M6', r'FinancialProjection', r'Financ'],
    'T': [r'M8', r'Team', r'Targets'],
    'IP': [r'Pitch', r'Deck', r'Investor', r'EBD8'],
    'L': [r'M7', r'Inclusion', r'Legal', r'Patent']
}

def get_ordered_doc_text(cat_dir, cat_code):
    all_files = [f for f in os.listdir(cat_dir) if f.endswith('.md')]
    patterns = CAT_DOC_PATTERNS.get(cat_code, [])
    
    # Priority files first, then others
    priority_files = []
    other_files = []
    for f in all_files:
        if any(re.search(p, f, re.IGNORECASE) for p in patterns):
            priority_files.append(f)
        else:
            other_files.append(f)
            
    sorted_files = sorted(priority_files) + sorted(other_files)
    
    doc_text = ""
    for f in sorted_files:
        p = os.path.join(cat_dir, f)
        try:
            with open(p, 'r', errors='ignore') as file:
                doc_text += f"=== DOCUMENT: {f} ===\n" + file.read() + "\n\n"
        except:
            pass
            
    return doc_text

def extract_single_question(q, doc_text):
    q_id = q.get('new_q_id', q.get('q_id'))
    q_simple = {
        'q_id': q_id,
        'category': q.get('cat_code'),
        'text': q['text'],
        'options': [o['val'] for o in q['options']]
    }
    
    prompt = f"""You are an objective due diligence evaluator analyzing a clean cleantech startup application.
Evaluate this single criterion against the provided clean document text.
Output a valid JSON object. Do NOT wrap in markdown or backticks.

<document>
{doc_text[:12000]}
</document>

<question>
{json.dumps(q_simple, indent=2)}
</question>

Output exactly one JSON object with these keys:
"q_id": "{q_id}"
"predicted_val": exactly one numeric value chosen from the provided options array
"confidence": float between 0.0 and 1.0 representing certainty
"citation": an exact verbatim quote of 1 to 2 COMPLETE, UNTRUNCATED sentences from the document providing the full context for your verdict (or null if no direct evidence exists)

STRICT CITATION RULES:
1. Complete Sentences Only: Never return a sentence fragment or cut off mid-thought. Quote the full enclosing sentence(s) so an external reader has full context.
2. Clean Narrative Only: Do NOT quote competition questions, instructions, or template placeholders. Only quote text written by the founders about their specific startup.
"""
    
    for attempt in range(3):
        try:
            resp = requests.post("http://127.0.0.1:46093/v1/chat/completions", json={
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.0,
                'max_tokens': 500,
            }, timeout=120)
            
            if resp.status_code == 200:
                data = resp.json()
                raw = data['choices'][0]['message']['content'].strip()
                
                if '```json' in raw: raw = raw.split('```json')[1].split('```')[0].strip()
                elif '```' in raw: raw = raw.split('```')[1].split('```')[0].strip()
                
                # If wrapped inside thinking brackets or text
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    raw = match.group(0)
                
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and 'q_id' in parsed:
                    # Sanitize citation: ensure it's not a tiny fragment
                    cit = parsed.get('citation')
                    if cit and len(cit.strip()) < 15:
                        parsed['citation'] = None
                    return parsed
                elif isinstance(parsed, list) and len(parsed) > 0 and 'q_id' in parsed[0]:
                    return parsed[0]
                    
        except Exception as e:
            pass
            
        time.sleep(2)
        
    return {
        'q_id': q_id,
        'predicted_val': None,
        'confidence': None,
        'citation': None
    }

def process_company(company, sample_limit=None):
    cache_path = os.path.join(CACHE_DIR, f"{company}.json")
    tmp_path = f"{cache_path}.tmp"
    
    cache_results = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cache_results = {r['q_id']: r for r in json.load(f)}
        except:
            pass
            
    cat_dir = os.path.join(RAW_BASE_DIR, company, 'converted')
    if not os.path.exists(cat_dir):
        print(f"[{company}] Directory not found: {cat_dir}", flush=True)
        return
        
    qs_to_run = [q for q in rubric if q.get('new_q_id', q.get('q_id')) not in cache_results]
    if sample_limit:
        qs_to_run = qs_to_run[:sample_limit]
        
    if not qs_to_run:
        print(f"[{company}] Already complete ({len(cache_results)}/{len(rubric)}). Skipping.", flush=True)
        return
        
    print(f"[{company}] Processing {len(qs_to_run)} questions (cache has {len(cache_results)})...", flush=True)
    
    # Preload docs by category to avoid constant disk reads
    cat_docs = {}
    for cat in CAT_DOC_PATTERNS.keys():
        cat_docs[cat] = get_ordered_doc_text(cat_dir, cat)
        
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for idx, q in enumerate(qs_to_run):
            q_id = q.get('new_q_id', q.get('q_id'))
            cat_code = q.get('cat_code', 'OTHER')
            doc_text = cat_docs.get(cat_code) or cat_docs.get('BC', '')
            
            futures[executor.submit(extract_single_question, q, doc_text)] = q_id
            
        for future in as_completed(futures):
            q_id = futures[future]
            try:
                start_time = time.time()
                res = future.result()
                duration = time.time() - start_time
                cache_results[q_id] = res
                
                with open(tmp_path, 'w') as f:
                    json.dump(list(cache_results.values()), f, indent=2)
                os.replace(tmp_path, cache_path)
                
                cit_preview = (res.get('citation') or '')[:70]
                if cit_preview: cit_preview = f' | Cit: "{cit_preview}..."'
                print(f"  -> {q_id} ({duration:.2f}s): Val={res.get('predicted_val')} Conf={res.get('confidence')}{cit_preview}", flush=True)
            except Exception as e:
                print(f"Error on {q_id}: {e}")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'ALL'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if target != 'ALL':
        process_company(target, limit)
    else:
        companies = sorted(os.listdir(RAW_BASE_DIR))
        companies = [c for c in companies if c != 'spark_inc' and not c.startswith('startup_test_')]
        print(f"Running clean extraction on {len(companies)} companies...")
        for c in companies:
            process_company(c)
        print("ALL COMPANIES COMPLETE.")
