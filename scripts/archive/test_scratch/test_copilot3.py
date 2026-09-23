import json
import requests

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'qwen3.6:35b'

prompt = """You are a strict startup evaluator. Read the document and evaluate these criteria.
Output a valid JSON array of objects. Do NOT wrap in markdown.

<document>
Test document. The startup has 10 patents.
</document>

<questions>
[
  {
    "q_id": "BC_Q1",
    "text": "How clearly is the value proposition understood?",
    "options": [1.0, 0.75, 0.5, 0.25, 0.0]
  }
]
</questions>

For each question, output:
"q_id": the question ID
"predicted_val": exactly one of the numeric values from the provided options array
"confidence": float between 0.0 and 1.0
"citation": exact verbatim quote from the document supporting the answer (or null if not found)
"""

try:
    resp = requests.post(OLLAMA_URL, json={
        'model': MODEL, 'prompt': prompt, 'stream': False, 
        'options': {'temperature': 0.0, 'num_predict': 1500}
    }, timeout=120)
    print("STATUS:", resp.status_code)
    data = resp.json()
    raw = data.get('response', '')
    print("RAW RESPONSE:")
    print(repr(raw))
except Exception as e:
    print("ERROR:", e)
