import json
import os
import requests
import concurrent.futures
import psycopg2

DB_URL = 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres'
OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'qwen3.6:35b'
BASE_DIR = '/data/scraping/datasets/cto_accelerator/parsed'
RUBRIC_PATH = '/tmp/scoring_interface_data.json'

with open(RUBRIC_PATH, 'r') as f:
    rubric = json.load(f)['ai_by_cat']

def extract_batch(cat_code, questions, document_text):
    q_text = '\n'.join([f"- ID: {q['new_q_id']} | Text: {q['text']}" for q in questions])
    prompt = f"""You are a strict startup due diligence evaluator.
Read the document and evaluate the following criteria.
You MUST reply with a valid JSON array. Do not include markdown formatting or thoughts.

<document>
{document_text[:8000]}
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
            'model': MODEL,
            'prompt': prompt,
            'format': 'json',
            'stream': False,
            'options': {'temperature': 0.0}
        }, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get('response', '').strip()
            if not raw and 'thinking' in data:
                raw = data['thinking'].strip()
            if '```json' in raw:
                raw = raw.split('```json')[1].split('```')[0].strip()
            elif '```' in raw:
                raw = raw.split('```')[1].split('```')[0].strip()
            return json.loads(raw)
    except Exception as e:
        print(f'Error parsing: {e}', flush=True)
    return []

def process_company(company_name):
    cat_dir = os.path.join(BASE_DIR, company_name, 'converted')
    md_text = ''
    for f in os.listdir(cat_dir):
        if f.endswith('.md'):
            with open(os.path.join(cat_dir, f), 'r', encoding='utf-8', errors='ignore') as file:
                md_text += file.read() + '\n\n'
                
    batches = []
    for cat_code, qs in rubric.items():
        binary_qs = [q for q in qs if q.get('type') == 'BINARY']
        for i in range(0, len(binary_qs), 5):
            batches.append((cat_code, binary_qs[i:i+5]))
            
    all_answers = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(extract_batch, b[0], b[1], md_text) for b in batches]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if isinstance(res, list):
                all_answers.extend(res)
            
    ai_cats = {}
    human_qs = []
    for cat_code, qs in rubric.items():
        ai_cats[cat_code] = {'questions': [], 'passed': 0, 'total': 0, 'full_name': cat_code}
        
    for ans in all_answers:
        if not isinstance(ans, dict) or 'q_id' not in ans: continue
        q_id = ans['q_id']
        cat = q_id.split('_')[0] if '_' in q_id else ''
        if cat not in ai_cats: continue
        
        entry = {
            'new_q_id': q_id,
            'cat_code': cat,
            'verdict': ans.get('verdict', 0),
            'confidence': ans.get('confidence', 0.0),
            'verbatim_citation': ans.get('citation')
        }
        
        if entry['confidence'] >= 0.85:
            ai_cats[cat]['questions'].append(entry)
        else:
            entry['ai_suggestion'] = entry['verdict']
            entry['ai_confidence'] = str(round(entry['confidence'], 2))
            human_qs.append(entry)
            
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT payload FROM startup_extractions WHERE startup_id = %s", (company_name,))
    payload = cur.fetchone()[0]
    
    payload['ai_cats'] = ai_cats
    payload['human_questions'] = human_qs
    
    cur.execute(
        "UPDATE startup_extractions SET payload = %s::jsonb WHERE startup_id = %s",
        (json.dumps(payload), company_name)
    )
    conn.commit()
    conn.close()
    print("FINISHED NOVAGRID!")

if __name__ == '__main__':
    process_company('Novagrid')
