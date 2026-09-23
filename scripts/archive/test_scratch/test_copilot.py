import json
import requests

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'qwen3.6:35b'

batch = [
    {
        "q_id": "BC_Q1",
        "text": "How clearly is the value proposition understood?",
        "options": [1.0, 0.75, 0.5, 0.25, 0.0]
    },
    {
        "q_id": "BC_Q2",
        "text": "Does the company clearly identify its customer segments and customer attributes?",
        "options": [1.0, 0.75, 0.5, 0.25, 0.0]
    }
]

doc_text = """
Executive Summary
SolarPure provides solar-powered water purification systems for rural communities.
Our value proposition is delivering clean water at 1/10th the cost of traditional infrastructure.
We target NGOs and local governments in Sub-Saharan Africa as our primary customer segments, focusing on areas with high sunlight and poor water quality.
"""

prompt = f"""You are a startup evaluator. Read the document and evaluate the following criteria.
Output a strict JSON array of objects. Do NOT wrap in markdown.

<document>
{doc_text}
</document>

<questions>
{json.dumps(batch, indent=2)}
</questions>

For each question, provide:
"q_id": the question ID
"predicted_val": select the most accurate numeric value from the provided options array
"confidence": float between 0.0 and 1.0
"citation": exact verbatim quote from the document (or null)
"""

resp = requests.post(OLLAMA_URL, json={
    'model': MODEL, 
    'prompt': prompt, 
    'format': 'json', 
    'stream': False, 
    'options': {'temperature': 0.0, 'num_predict': 1000}
})

data = resp.json()
raw = data.get('response', '').strip()
if '```json' in raw: raw = raw.split('```json')[1].split('```')[0].strip()
elif '```' in raw: raw = raw.split('```')[1].split('```')[0].strip()

print("RAW OUTPUT:")
print(raw)
try:
    parsed = json.loads(raw)
    print("PARSED OK")
except Exception as e:
    print(e)
