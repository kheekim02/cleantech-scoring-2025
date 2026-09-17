import os, re
import pandas as pd
import numpy as np

def run_transformations():
    proc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed"))
    meta_path = os.path.join(proc_dir, "master_questions_metadata.csv")
    raw_master_path = os.path.join(proc_dir, "master_raw_startup_dataset.csv")

    df_meta = pd.read_csv(meta_path)
    df_raw = pd.read_csv(raw_master_path, low_memory=False)

    print("1. Running transformations across archetypes...")
    
    # Track new columns in a dictionary to prevent fragmentation
    new_cols = {}

    cat_map = {
        "Business Canvas": "BC", "Impact/ Sustainability": "IS", "Product/ Market Fit": "PMF",
        "Markets": "M", "Tech and Product": "TP", "Financials": "F", "Legal": "L",
        "Team": "T", "Executive Summary": "ES", "Investor Pitch": "IP"
    }

    def get_cat_code(cat_sec):
        for k, v in cat_map.items():
            if k.lower() in cat_sec.lower():
                return v
        return "Q"

    # A. Binary & Ladder Questions
    for idx, q_row in df_meta.iterrows():
        archetype = q_row["archetype"]
        cat_sec = str(q_row["category_section"])
        q_num = str(q_row["question_number_in_cat"])
        cat_code = get_cat_code(cat_sec)
        
        s1_col = f"{cat_code}_Scorer_1_Q{q_num}"
        s2_col = f"{cat_code}_Scorer_2_Q{q_num}"
        mean_col = f"mean_{cat_code}_Q{q_num}"

        if archetype in ["BINARY", "CUMULATIVE_LADDER"]:
            if s1_col in df_raw.columns:
                s1 = pd.to_numeric(df_raw[s1_col], errors="coerce")
                s2 = pd.to_numeric(df_raw[s2_col], errors="coerce") if s2_col in df_raw.columns else s1
                mean_v = pd.to_numeric(df_raw[mean_col], errors="coerce") if mean_col in df_raw.columns else s1

                # Conflict flag (1 if raters disagreed)
                conflict = (s1.notna() & s2.notna() & (s1 != s2))
                new_cols[f"{cat_code}_Q{q_num}_conflict_flag"] = conflict.astype(int)

                # Resolved boolean (1 if mean >= 0.5, 0 if < 0.5, NaN if missing)
                resolved = np.where(mean_v >= 0.5, 1, np.where(mean_v.notna(), 0, np.nan))
                new_cols[f"{cat_code}_Q{q_num}_resolved_bool"] = resolved

        elif archetype == "CONDITIONAL_NA":
            if mean_col in df_raw.columns:
                mean_v = pd.to_numeric(df_raw[mean_col], errors="coerce")
                # Rule: if missing/NA, default to 1.0 per policy
                new_cols[f"{cat_code}_Q{q_num}_resolved_score"] = mean_v.fillna(1.0)

    # Attach generated feature columns at once
    new_df = pd.DataFrame(new_cols, index=df_raw.index)
    df_transformed = pd.concat([df_raw, new_df], axis=1)

    # B. Monotonicity Correction on Cumulative Customer Interview Ladders
    for prefix in ["PMF"]:
        q3_col = f"{prefix}_Q3_resolved_bool"
        q4_col = f"{prefix}_Q4_resolved_bool"
        q5_col = f"{prefix}_Q5_resolved_bool"

        if q3_col in df_transformed.columns and q4_col in df_transformed.columns and q5_col in df_transformed.columns:
            # If Q5 == 1 -> Q4 = 1, Q3 = 1; If Q4 == 1 -> Q3 = 1
            df_transformed[q4_col] = np.where(df_transformed[q5_col] == 1, 1, df_transformed[q4_col])
            df_transformed[q3_col] = np.where((df_transformed[q5_col] == 1) | (df_transformed[q4_col] == 1), 1, df_transformed[q3_col])

            df_transformed["customer_interview_tier"] = np.where(
                df_transformed[q5_col] == 1, "10+_Interviews",
                np.where(df_transformed[q4_col] == 1, "6-9_Interviews",
                np.where(df_transformed[q3_col] == 1, "4-5_Interviews", "0-3_Interviews"))
            )

    # C. Structured Funding Amount ($M) Parsing
    funding_cols = [c for c in df_transformed.columns if "Total (disclosed) Funding Amount" in c or "Total" in c and "Funding" in c]
    if funding_cols:
        f_col = funding_cols[0]

        def parse_funding_clean(val):
            if pd.isna(val):
                return np.nan
            val_str = str(val).replace("$", "").replace(",", "").strip()
            if val_str == "" or val_str.lower() in ["nan", "n/a", "none", "-", "n"]:
                return np.nan
            try:
                if "m" in val_str.lower():
                    return float(re.sub(r"[^\d.]", "", val_str))
                elif "k" in val_str.lower():
                    return float(re.sub(r"[^\d.]", "", val_str)) / 1000.0
                elif "b" in val_str.lower():
                    return float(re.sub(r"[^\d.]", "", val_str)) * 1000.0
                else:
                    num = float(re.sub(r"[^\d.]", "", val_str))
                    if num > 10000:
                        return num / 1_000_000.0
                    return num
            except:
                return np.nan

        df_transformed["funding_total_usd_millions"] = df_transformed[f_col].apply(parse_funding_clean)

    out_path = os.path.join(proc_dir, "master_transformed_dataset.csv")
    df_transformed.to_csv(out_path, index=False)
    print(f"Transformed Dataset generated: {df_transformed.shape} -> {out_path}")

if __name__ == '__main__':
    run_transformations()
