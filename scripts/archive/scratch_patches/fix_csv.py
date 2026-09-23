import csv

input_file = 'data/processed/master_decomposed_rubric_inventory.csv'
output_file = 'data/processed/master_decomposed_rubric_inventory_fixed.csv'

with open(input_file, 'r') as fin, open(output_file, 'w', newline='') as fout:
    reader = csv.DictReader(fin)
    writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
    writer.writeheader()
    
    for row in reader:
        # Fix the ES_ -> IS_ typos
        orig = row['orig_q_id']
        if orig in ['ES_Q7', 'ES_Q10', 'ES_Q11', 'ES_Q16', 'ES_Q18', 'ES_Q19', 'ES_Q20', 'ES_Q23', 'ES_Q32']:
            row['orig_q_id'] = orig.replace('ES_', 'IS_')
            row['new_q_id'] = row['new_q_id'].replace('ES_', 'IS_')
            # Category was probably wrong too. Let's fix it if it says "Impact/ Sustainability"
            if row['cat_code'] == 'ES':
                row['cat_code'] = 'IS'
                row['category'] = '9. Executive Summary'
        
        # Another one: IP_Q22
        # IP_Q22 [ORIGINAL] Does the presentation discuss current and potential competitors (Incumbents, Startups, In-House, Substitutes)?
        # 363 mapping is fine, just NLP script didn't match perfectly.
        
        writer.writerow(row)

import os
os.replace(output_file, input_file)
print("Fixed CSV typos!")
