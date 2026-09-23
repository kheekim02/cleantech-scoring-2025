import json

with open('master_282_rubric.json', 'r') as f:
    r282 = json.load(f)

dict_282 = {q.get('new_q_id', q.get('q_id')): q for q in r282}

SUBJECTIVE_IDS = [
    'BC_Q1', 'BC_Q2', 'BC_Q3', 'BC_Q4', 'BC_Q5',
    'IS_Q7', 'IS_Q16',
    'PMF_Q15', 'PMF_Q17',
    'TP_Q13', 'TP_Q14', 'TP_Q15',
    'F_Q22', 'F_Q23', 'F_Q24',
    'IP_Q22', 'IP_Q50'
]

cat_names = {
    'BC': 'Business Model Canvas',
    'IS': 'Executive Summary / Impact Strategy',
    'PMF': 'Product-Market Fit & Customer Discovery',
    'TP': 'Tech / Product Validation',
    'F': 'Financials & Funding',
    'IP': 'Investor Pitch Deck'
}

html_path = "/Users/geoffrey/Desktop/Rubric_Binarization_Review.html"

html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Subjective Rubric Questions Review</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 960px; margin: 40px auto; color: #1e293b; background: #f8fafc; padding: 0 20px; }
        h1 { text-align: center; color: #0f172a; margin-bottom: 6px; }
        .subtitle { text-align: center; color: #64748b; font-size: 15px; margin-bottom: 36px; }
        .card { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); display: flex; gap: 20px; align-items: flex-start; }
        .qid-badge { font-family: ui-monospace, monospace; font-size: 13px; font-weight: 700; color: #dc2626; background: #fef2f2; border: 1px solid #fee2e2; padding: 4px 10px; border-radius: 6px; white-space: nowrap; }
        .cat-tag { font-size: 12px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
        .text { font-size: 15px; color: #1e293b; font-weight: 500; line-height: 1.5; }
    </style>
</head>
<body>
    <h1>Subjective Rubric Questions</h1>
    <p class="subtitle">Filtered list of the 17 most qualitative, judgment-dependent questions in the rubric (cleanly binarized questions omitted).</p>
"""

for qid in SUBJECTIVE_IDS:
    q_obj = dict_282.get(qid, {})
    text = q_obj.get('text', '')
    cat = qid.split('_')[0]
    cat_name = cat_names.get(cat, cat)
    html += f"""
    <div class="card">
        <div class="qid-badge">{qid}</div>
        <div style="flex:1;">
            <div class="cat-tag">{cat_name}</div>
            <div class="text">{text}</div>
        </div>
    </div>
    """

html += "</body></html>"

with open(html_path, 'w') as f:
    f.write(html)

print("Updated HTML at:", html_path)
