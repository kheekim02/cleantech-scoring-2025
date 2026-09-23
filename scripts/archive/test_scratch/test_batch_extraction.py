import json
import os
import re
import requests
import concurrent.futures
from time import perf_counter

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.6:35b"

with open("data/processed/scoring_interface_data.json", "r") as f:
    rubric = json.load(f)["ai_by_cat"]

test_rubric = {"BC": rubric["BC"][:5]}

def extract_batch(cat_code, questions):
    q_text = "\n".join([f"- ID: {q['new_q_id']} | Text: {q['text']}" for q in questions])
    
    prompt = f"""You are a strict startup due diligence evaluator.
Read the document and evaluate the following criteria.

<document>
Company Name: 2DaLoop
Revenue Projections: $2.1M by year 3.
Business Model: B2B SaaS for E-Waste recycling and tracking.
Sustainability: Diverts 500 tons of e-waste from landfills annually.
Team: 2 Founders, no previous exits.
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
    
    t0 = perf_counter()
    resp = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0}
    })
    elapsed = perf_counter() - t0
    
    if resp.status_code == 200:
        raw = resp.json()["response"]
        print("RAW RESPONSE:", raw)
        return
        
extract_batch("BC", test_rubric["BC"])
