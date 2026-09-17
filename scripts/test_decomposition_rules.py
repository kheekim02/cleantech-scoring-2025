import pandas as pd
import re

meta = pd.read_csv('data/processed/master_questions_metadata.csv')
flagged = pd.read_csv('data/processed/flagged_questions_for_binarization.csv')

print(f"Meta: {len(meta)}, Flagged: {len(flagged)}")

# Let's inspect each section's questions and see how many decompose
# We can create a mapping for all 282 questions
