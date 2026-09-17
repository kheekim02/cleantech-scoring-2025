import pandas as pd
import numpy as np

# Load metadata
df_meta = pd.read_csv('data/processed/master_questions_metadata.csv')

# Let's inspect the distribution of is_objective and archetype
print("Original questions:", len(df_meta))
print("Objective vs Subjective in original:")
print(df_meta['is_objective'].value_counts())
