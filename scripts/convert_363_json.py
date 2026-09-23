import csv
import json

input_csv = 'data/processed/master_decomposed_rubric_inventory.csv'
output_json = 'master_363_rubric.json'

out_data = []
with open(input_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        out_data.append({
            "q_id": row["new_q_id"],
            "text": row["text"],
            "options": [
                {"val": 1, "label": "YES"},
                {"val": 0, "label": "NO"}
            ]
        })

with open(output_json, 'w') as f:
    json.dump(out_data, f, indent=2)

print(f"Generated {output_json} with {len(out_data)} questions.")
