import os, re
import pandas as pd
import numpy as np

def clean_name(s):
    if pd.isna(s):
        return ""
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\b(inc|llc|corp|corporation|co|technologies|technology|energy|solutions|group)\b", "", s)
    return " ".join(s.split())

def make_company_id(name_clean, year):
    slug = re.sub(r"\s+", "_", name_clean)
    yr = str(int(year)) if pd.notna(year) and str(year).replace(".0","").isdigit() else "unknown"
    return f"cto_{slug}_{yr}"

def main():
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/raw"))
    proc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed"))
    os.makedirs(proc_dir, exist_ok=True)

    excel_path = os.path.join(raw_dir, "cleaned+matched_versus_normalized_v3.xlsx")
    csv_path = os.path.join(raw_dir, "CTO Startup Outcomes Spring 2026 - Spring 2026.csv")
    q_csv_path = os.path.join(raw_dir, "Scoring Edited Questions List - Finalized Question List.csv")

    print("1. Loading Question Metadata...")
    q_df_raw = pd.read_csv(q_csv_path)

    current_cat = "General"
    question_meta = []
    for idx, r in q_df_raw.iterrows():
        val0 = r.iloc[0]
        q_txt = str(r["Question"]).strip()
        if pd.isna(val0) and q_txt and q_txt != "nan":
            current_cat = q_txt
        elif pd.notna(val0) and q_txt and q_txt != "nan":
            try:
                q_num = int(float(val0))
            except:
                q_num = str(val0)
            
            obj_flag = r.iloc[4] if len(r) > 4 and pd.notna(r.iloc[4]) else (r.iloc[3] if len(r) > 3 and pd.notna(r.iloc[3]) else None)
            
            question_meta.append({
                "category_section": current_cat,
                "question_number_in_cat": q_num,
                "question_text": q_txt,
                "allowed_score_range": str(r.get("Range", "")),
                "is_objective": 1 if str(obj_flag).strip() in ["1", "1.0"] else (0 if str(obj_flag).strip() in ["0", "0.0"] else None),
                "needs_review": str(r.get("Needs review?", ""))
            })

    df_qmeta = pd.DataFrame(question_meta)
    df_qmeta["global_question_id"] = range(1, len(df_qmeta) + 1)
    df_qmeta.to_csv(os.path.join(proc_dir, "master_questions_metadata.csv"), index=False)
    print(f"Saved master questions metadata: {len(df_qmeta)} questions.")

    print("\n2. Loading Matched and Normalized Rubric Scores...")
    matched_df = pd.read_excel(excel_path, sheet_name="matched_scores")
    norm_df = pd.read_excel(excel_path, sheet_name="normalized_scores_mean")

    matched_df["clean_name"] = matched_df["Company Name (original)"].apply(clean_name)
    norm_df["clean_name"] = norm_df["Company Name (original)"].apply(clean_name)
    matched_df["company_id"] = [make_company_id(cn, yr) for cn, yr in zip(matched_df["clean_name"], matched_df.get("Year", [None]*len(matched_df)))]

    scorer1_cols = [c for c in matched_df.columns if "Scorer_1" in c]
    scorer2_cols = [c for c in matched_df.columns if "Scorer_2" in c]
    mean_q_cols = [c for c in norm_df.columns if "_Q" in c and c not in scorer1_cols and c not in scorer2_cols]

    base_rubric = matched_df[["company_id", "clean_name", "Company Name (original)", "Company Name", "Year", "Founder"] + scorer1_cols + scorer2_cols].copy()
    norm_subset = norm_df[["clean_name"] + mean_q_cols].copy()
    norm_subset = norm_subset.rename(columns={c: f"mean_{c}" for c in mean_q_cols})

    rubric_merged = pd.merge(base_rubric, norm_subset, on="clean_name", how="left")
    rubric_merged = rubric_merged.drop_duplicates(subset=["company_id"]).reset_index(drop=True)
    print(f"Unified Rubric Table constructed: {rubric_merged.shape}")

    print("\n3. Loading Outcomes CSV...")
    raw_csv = pd.read_csv(csv_path, skiprows=1)
    df_outcomes = raw_csv.iloc[5:].copy().reset_index(drop=True)

    col_names = []
    for c in range(raw_csv.shape[1]):
        parts = []
        for r in range(5):
            val = raw_csv.iloc[r, c]
            if pd.notna(val) and not str(val).startswith("Unnamed") and str(val).strip():
                parts.append(str(val).strip())
        if parts:
            clean_col = " -> ".join(parts[:2]) if len(parts) > 1 else parts[0]
        else:
            clean_col = f"outcome_col_{c}"
        col_names.append(clean_col)

    seen = {}
    unique_cols = []
    for c in col_names:
        if c not in seen:
            seen[c] = 1
            unique_cols.append(c)
        else:
            seen[c] += 1
            unique_cols.append(f"{c}_{seen[c]}")

    df_outcomes.columns = unique_cols
    df_outcomes["clean_name"] = df_outcomes.iloc[:, 0].apply(clean_name)

    print("\n4. Compiling Master Raw Dataset...")
    master_raw = pd.merge(
        rubric_merged,
        df_outcomes,
        on="clean_name",
        how="outer",
        suffixes=("", "_outcomes_raw")
    )

    for idx, r in master_raw.iterrows():
        if pd.isna(r["company_id"]):
            name = r.iloc[len(rubric_merged.columns)]
            year = r.iloc[len(rubric_merged.columns) + 3]
            clean_n = clean_name(name)
            master_raw.at[idx, "company_id"] = make_company_id(clean_n, year)
            master_raw.at[idx, "Company Name (original)"] = name
            master_raw.at[idx, "clean_name"] = clean_n

    master_raw = master_raw.drop_duplicates(subset=["company_id"]).reset_index(drop=True)

    output_csv_path = os.path.join(proc_dir, "master_raw_startup_dataset.csv")
    master_raw.to_csv(output_csv_path, index=False)
    print(f"\n=======================================================")
    print(f"SUCCESS: Compiled Master Raw Dataset!")
    print(f"Total Startups: {len(master_raw)} rows")
    print(f"Total Columns:  {len(master_raw.columns)} atomic columns")
    print(f"Saved to: {output_csv_path}")
    print(f"=======================================================")

if __name__ == "__main__":
    main()
