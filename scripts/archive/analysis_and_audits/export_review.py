import json
import csv
import os

html_path = "/Users/geoffrey/Desktop/Rubric_Binarization_Review.html"
csv_path = "/Users/geoffrey/Desktop/Rubric_Binarization_Review.csv"

# Load 282
with open('master_282_rubric.json', 'r') as f:
    r282 = json.load(f)

dict_282 = {q.get('new_q_id', q.get('q_id')): q['text'] for q in r282}

# Load 363 CSV (the fixed one)
clusters = {}
with open('data/processed/master_decomposed_rubric_inventory.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        orig = row['orig_q_id']
        if orig not in clusters:
            clusters[orig] = []
        clusters[orig].append({'id': row['new_q_id'], 'text': row['text']})

# Filter to only binarized (len > 1)
binarized = {k: v for k, v in clusters.items() if len(v) > 1}

# --- GENERATE HTML ---
html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Rubric Binarization Review</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; max-width: 900px; margin: 40px auto; color: #333; background: #f3f4f6; padding: 0 20px; }
        h1 { text-align: center; color: #111827; margin-bottom: 8px; }
        .cluster { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
        .parent { font-size: 15px; font-weight: 600; color: #1f2937; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #f3f4f6; line-height: 1.4; }
        .parent-id { color: #2563eb; font-family: ui-monospace, monospace; font-size: 13px; background: #eff6ff; padding: 4px 8px; border-radius: 6px; margin-right: 12px; }
        .children { list-style: none; padding-left: 0; margin: 0; }
        .child { padding: 12px 16px; margin-bottom: 8px; background: #f8fafc; border-left: 4px solid #10b981; border-radius: 4px; display: flex; gap: 16px; align-items: flex-start; }
        .child-id { font-family: ui-monospace, monospace; font-size: 13px; color: #059669; font-weight: 700; white-space: nowrap; padding-top: 2px; }
        .child-text { font-size: 14px; color: #334155; line-height: 1.4; }
    </style>
</head>
<body>
    <h1>Rubric Binarization Review</h1>
    <p style="text-align:center; color:#6b7280; margin-bottom: 40px;">Total multi-part questions decomposed: """ + str(len(binarized)) + """</p>
"""

for orig_id in sorted(binarized.keys()):
    orig_text = dict_282.get(orig_id, "TEXT NOT FOUND IN 282 RUBRIC")
    children = binarized[orig_id]
    
    html += f'<div class="cluster">'
    html += f'<div class="parent"><span class="parent-id">{orig_id}</span> {orig_text}</div>'
    html += f'<ul class="children">'
    for c in children:
        html += f'<li class="child"><span class="child-id">{c["id"]}</span><span class="child-text">{c["text"]}</span></li>'
    html += f'</ul></div>'

html += "</body></html>"

with open(html_path, 'w') as f:
    f.write(html)

# --- GENERATE CSV ---
with open(csv_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Parent_ID", "Parent_Text", "Binary_Child_ID", "Binary_Child_Text", "Reviewer_Approved", "Reviewer_Notes"])
    
    for orig_id in sorted(binarized.keys()):
        orig_text = dict_282.get(orig_id, "TEXT NOT FOUND IN 282 RUBRIC")
        children = binarized[orig_id]
        for c in children:
            writer.writerow([orig_id, orig_text, c["id"], c["text"], "", ""])

print(f"Exported HTML to {html_path}")
print(f"Exported CSV to {csv_path}")
