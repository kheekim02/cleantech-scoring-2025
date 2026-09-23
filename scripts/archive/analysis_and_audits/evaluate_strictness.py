import json
import csv
import requests

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'deepseek-coder-v2:16b'

with open('master_282_rubric.json', 'r') as f:
    r282 = json.load(f)

dict_282 = {q.get('new_q_id', q.get('q_id')): q['text'] for q in r282}

clusters = {}
with open('data/processed/master_decomposed_rubric_inventory.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        orig = row['orig_q_id']
        if orig not in clusters: clusters[orig] = []
        clusters[orig].append({'id': row['new_q_id'], 'text': row['text']})

binarized = {k: v for k, v in clusters.items() if len(v) > 1}

results = []

for orig_id, children in binarized.items():
    orig_text = dict_282.get(orig_id, "")
    if not orig_text: continue
    
    child_text = "\n".join([f"- {c['id']}: {c['text']}" for c in children])
    
    prompt = f"""You are an expert rubric auditor. Compare this original subjective question to its new binary sub-questions. 
Does combining the binary sub-questions mathematically and wholly equate to the original question? Or do the binary questions introduce strict, objective, or highly specific requirements (like "metrics", "tables", "specific titles", "incumbents") that were NEVER explicitly mandated in the broad original question?

Original Question ({orig_id}):
"{orig_text}"

New Binary Sub-Questions:
{child_text}

Output EXACTLY one word on the first line: "CLEAN" if they wholly equate, or "MISMATCH" if the new questions introduce strictness/scope creep that prevents a clean breakoff.
If MISMATCH, output a one-sentence explanation on the second line.
"""
    
    try:
        resp = requests.post(OLLAMA_URL, json={
            'model': MODEL, 'prompt': prompt, 'stream': False, 'options': {'temperature': 0.0}
        }).json()
        
        reply = resp['response'].strip().split('\n')
        verdict = reply[0].strip().upper()
        if 'MISMATCH' in verdict:
            reason = reply[1] if len(reply) > 1 else "Introduced new strict requirements."
            results.append(f"### {orig_id}\n**Original:** {orig_text}\n**Children:**\n{child_text}\n**Mismatch Reason:** {reason}\n")
            print(f"Flagged: {orig_id}")
    except Exception as e:
        print(f"Error on {orig_id}: {e}")

with open('/Users/geoffrey/Desktop/Strictness_Creep_Report.md', 'w') as f:
    f.write("# Clean Breakoff Failures (Strictness Creep)\n\n")
    f.write("These instances were flagged because the binarized questions introduced strict, quantitative, or highly specific formatting requirements that were not explicitly mandated in the broader, qualitative original question.\n\n")
    f.write("\n---\n".join(results))
    
print("Done.")
