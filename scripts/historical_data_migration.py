import pandas as pd
import numpy as np

def migrate_historical_data(legacy_csv_path, output_csv_path):
    """
    Migrates historical 282-question format to the new 363-question binary format.
    Uses deterministic reverse-mapping for ordinal tiers and compound rules where possible.
    Leaves non-deterministic subjective fields as NaN for future AI/human backfill.
    """
    # Load legacy dataset
    try:
        df_legacy = pd.read_csv(legacy_csv_path)
    except Exception as e:
        print(f"Error loading {legacy_csv_path}: {e}")
        return

    df_new = pd.DataFrame()
    df_new['startup_id'] = df_legacy.get('startup_id', df_legacy.index)
    df_new['startup_name'] = df_legacy.get('startup_name', 'Unknown')
    
    # Example deterministic mapping:
    # Legacy Funding Tier (T_Q26):
    # 0 = <$250k, 0.5 = $250k-$2M, 1 = >$2M
    # New Atomic Gates: T_Q26a (>= $250k), T_Q26b (>= $2M)
    
    if 'T_Q26' in df_legacy.columns:
        df_new['T_Q26a'] = df_legacy['T_Q26'].apply(lambda x: 1 if pd.notnull(x) and x >= 0.5 else 0 if pd.notnull(x) else np.nan)
        df_new['T_Q26b'] = df_legacy['T_Q26'].apply(lambda x: 1 if pd.notnull(x) and x == 1.0 else 0 if pd.notnull(x) else np.nan)
    
    # Example Compound Rule:
    # Legacy BC_Q5 (Small sections of BMC filled):
    # If legacy is 1.0, then all sub-components must be 1.0. If legacy < 1.0, we don't know which failed -> NaN
    
    if 'BC_Q5' in df_legacy.columns:
        for sub in ['BC_Q5a', 'BC_Q5b', 'BC_Q5c', 'BC_Q5d']:
            df_new[sub] = df_legacy['BC_Q5'].apply(lambda x: 1 if x == 1.0 else np.nan)
            
    # For Subjective Questions (e.g. IP_Q5 "Compelling pain point")
    # We leave these as NaN so the AI Inference pipeline can backfill them using the original PDFs
    if 'IP_Q5' in df_legacy.columns:
        df_new['IP_Q5'] = np.nan

    # Export
    df_new.to_csv(output_csv_path, index=False)
    print(f"Migrated data saved to {output_csv_path}. Indeterminate fields marked as NaN.")

if __name__ == "__main__":
    # Example usage:
    # migrate_historical_data('data/raw/CTO Startup Outcomes Spring 2026 - Spring 2026.csv', 'data/processed/migrated_363_scores.csv')
    pass
