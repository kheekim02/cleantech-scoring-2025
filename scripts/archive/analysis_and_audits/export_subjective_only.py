import json
import csv

# Load 282
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

# CSV Export
csv_path = "/Users/geoffrey/Desktop/Subjective_Rubric_Questions.csv"
with open(csv_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Question_ID", "Category_Code", "Category_Name", "Question_Text", "Scoring_Guidance_Notes"])
    for qid in SUBJECTIVE_IDS:
        q_obj = dict_282.get(qid, {})
        text = q_obj.get('text', '')
        cat = qid.split('_')[0]
        cat_name = cat_names.get(cat, cat)
        notes = ""
        writer.writerow([qid, cat, cat_name, text, notes])

# Markdown Export
md_path = "/Users/geoffrey/Desktop/Subjective_Rubric_Questions.md"
with open(md_path, 'w') as f:
    f.write("# Highly Subjective Rubric Questions (Human Scorer Review Required)\n\n")
    f.write("These 17 questions represent the most qualitative, judgment-dependent questions in the rubric. ")
    f.write("Unlike mechanical checks, these questions require human evaluator discretion rather than rigid binary metrics.\n\n")
    f.write("| # | Question ID | Category | Question Text |\n")
    f.write("| :---: | :--- | :--- | :--- |\n")
    for idx, qid in enumerate(SUBJECTIVE_IDS, 1):
        q_obj = dict_282.get(qid, {})
        text = q_obj.get('text', '').replace('\n', ' ')
        cat = qid.split('_')[0]
        cat_name = cat_names.get(cat, cat)
        f.write(f"| {idx} | `{qid}` | {cat_name} | {text} |\n")

print(f"Exported {len(SUBJECTIVE_IDS)} subjective questions to:")
print(f" - {csv_path}")
print(f" - {md_path}")
