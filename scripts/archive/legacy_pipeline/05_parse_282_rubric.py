import csv
import json
import re

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

def parse_range(range_str):
    range_str = range_str.strip('[]').replace(' ', '')
    if not range_str: return []
    vals = range_str.split(',')
    options = []
    for v in vals:
        try:
            val = float(v)
            label = f"{val} PTS" if val != 1.0 else "1 PT"
            options.append({"label": label, "val": val})
        except:
            pass
    # Sort descending (e.g. 1 PT, 0.5 PTS, 0 PTS)
    options.sort(key=lambda x: x["val"], reverse=True)
    return options

questions = []
current_cat = None

with open("./data/raw/Scoring Edited Questions List - Finalized Question List.csv", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader) # skip header
    for row in reader:
        col0, col1, col2 = row[0].strip(), row[1].strip(), row[2].strip()
        
        # Check if it's a category header
        if not col0 and col1:
            # Match start of category
            for key, val in CAT_MAP.items():
                if col1.startswith(key):
                    current_cat = val
                    break
            continue
            
        # Check if it's a valid question
        if col0.isdigit() and current_cat:
            q_id = f"{current_cat}_Q{col0}"
            options = parse_range(col2)
            if not options:
                # Default binary if missing
                options = [{"label": "1 PT", "val": 1.0}, {"label": "0 PTS", "val": 0.0}]
                
            questions.append({
                "q_id": q_id,
                "cat_code": current_cat,
                "text": col1,
                "options": options
            })

with open("./master_282_rubric.json", "w") as f:
    json.dump(questions, f, indent=2)

print(f"Successfully parsed {len(questions)} questions into master_282_rubric.json")
