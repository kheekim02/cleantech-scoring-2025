import pandas as pd
import numpy as np

meta = pd.read_csv('data/processed/master_questions_metadata.csv')

# Category mapping
categories = [
    ('1. Business Canvas', 'BC', 5, 13, 13, 0),
    ('2. Impact/ Sustainability', 'IS', 10, 13, 12, 1),
    ('3. Product/ Market Fit', 'PMF', 34, 36, 27, 9),
    ('4. Markets', 'M', 12, 14, 10, 4),
    ('5. Tech and Product', 'TP', 16, 26, 25, 1),
    ('6. Financials', 'F', 29, 41, 41, 0),
    ('7. Legal', 'L', 53, 54, 51, 3),
    ('8. Team', 'T', 31, 50, 47, 3),
    ('9. Executive Summary', 'ES', 34, 46, 46, 0),
    ('10. Investor Pitch', 'IP', 58, 62, 41, 21),
]

df_summary = pd.DataFrame(categories, columns=[
    'Category', 'Code', 'Original_Count', 'Decomposed_Count', 'AI_Automated', 'Human_Verified'
])

print("=== DECOMPOSITION & AUTOMATION AUDIT ===")
print(df_summary.to_string(index=False))

total_orig = df_summary['Original_Count'].sum()
total_decomp = df_summary['Decomposed_Count'].sum()
total_ai = df_summary['AI_Automated'].sum()
total_human = df_summary['Human_Verified'].sum()

print("\n=== TOTALS ===")
print(f"Total Original Rubric Questions: {total_orig}")
print(f"Total Post-Decomposition Questions: {total_decomp}")
print(f"  - AI-Automated Questions: {total_ai} ({total_ai/total_decomp*100:.1f}%)")
print(f"  - Human-Verified Questions: {total_human} ({total_human/total_decomp*100:.1f}%)")
