import csv
import json
from collections import Counter

# Load JSON
with open('master_282_rubric.json', 'r') as f:
    json_data = json.load(f)

json_total = len(json_data)
json_cat_counts = Counter(q['cat_code'] for q in json_data)

# Load CSV
csv_cat_counts = Counter()
csv_total = 0
CAT_MAP = {
    '1. Business Canvas': 'BC',
    '2. Impact/ Sustainability': 'ES',
    '3. Product/ Market Fit': 'PMF',
    '4. Markets': 'M',
    '5. Tech and Product': 'TP',
    '6. Financials': 'F',
    '7. Legal': 'L',
    '8. Team': 'T',
    '9. Executive Summary': 'IS',
    '10. Investor Pitch': 'IP'
}
current_cat = None

with open('./data/raw/Scoring Edited Questions List - Finalized Question List.csv', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        col0, col1 = row[0].strip(), row[1].strip()
        if not col0 and col1:
            for key, val in CAT_MAP.items():
                if col1.startswith(key):
                    current_cat = val
                    break
            continue
        if col0.isdigit() and current_cat:
            csv_cat_counts[current_cat] += 1
            csv_total += 1

# Analyze Options (Labels/Scales)
scale_signatures = Counter()
multipart_issues = []
for q in json_data:
    # create a signature like "1.0, 0.5, 0.0"
    sig = ", ".join([str(o['val']) for o in q['options']])
    scale_signatures[sig] += 1
    
    # Heuristic check: does the text imply 3 parts but signature has 2?
    text = q['text'].lower()
    if '0.5' in text or '0.25' in text or '1 pt' in text:
        if len(q['options']) <= 2 and not ('0,1' in sig or '0.0, 1.0' in sig):
            multipart_issues.append((q['q_id'], sig, q['text']))

print(f"--- CHECK 2: TOTAL QUESTIONS ---")
print(f"CSV Total: {csv_total}")
print(f"JSON Total: {json_total}")
print(f"Match: {csv_total == json_total == 282}\n")

print(f"--- CHECK 3: CATEGORY COUNTS ---")
for cat in CAT_MAP.values():
    print(f"{cat:4}: CSV={csv_cat_counts[cat]}, JSON={json_cat_counts[cat]} -> {'Match' if csv_cat_counts[cat] == json_cat_counts[cat] else 'MISMATCH'}")
print()

print(f"--- CHECK 1: MULTIPART LABELS ---")
print("Distinct Point Scales Found:")
for sig, count in scale_signatures.items():
    print(f"  [{sig}] -> {count} questions")

if multipart_issues:
    print("\nWARNING: Possible mismatches between text and parsed scale:")
    for issue in multipart_issues:
        print(f"  {issue[0]}: Parsed [{issue[1]}] | Text: {issue[2][:80]}...")
else:
    print("\nNo obvious mismatches detected between question text and parsed scales.")
