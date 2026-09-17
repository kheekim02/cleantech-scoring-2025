import os, re
import pandas as pd
import numpy as np

def run_evolution():
    proc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed"))
    input_path = os.path.join(proc_dir, "master_transformed_dataset.csv")
    meta_path = os.path.join(proc_dir, "master_questions_metadata.csv")

    print("1. Loading Transformed Master Dataset...")
    df = pd.read_csv(input_path, low_memory=False)
    df_meta = pd.read_csv(meta_path)
    print(f"Loaded input data shape: {df.shape}")

    # Track all newly engineered features in a dict
    new_features = {}

    # ==========================================
    # LAYER 1: TEMPORAL HORIZON EQUALIZATION
    # ==========================================
    print("2. Layer 1: Computing Temporal Horizon & Velocity Metrics...")
    
    # Extract clean cohort year (clamp between 2016 and 2024)
    def parse_year(val):
        try:
            if pd.notna(val):
                y = int(float(str(val).strip()))
                if 2000 <= y <= 2026:
                    return y
        except:
            pass
        return 2018 # default median
        
    cohort_years = df["Year"].apply(parse_year)
    lifespans = np.maximum(2026 - cohort_years, 1)
    
    new_features["cohort_year_clean"] = cohort_years
    new_features["lifespan_years_observed"] = lifespans
    
    # Vintage grouping
    new_features["vintage_cohort_group"] = np.where(
        cohort_years <= 2018, "2016-2018_Mature",
        np.where(cohort_years <= 2021, "2019-2021_Growth", "2022-2024_Early")
    )
    
    # Funding velocity ($M per year active)
    funding_m = pd.to_numeric(df.get("funding_total_usd_millions", 0.0), errors="coerce").fillna(0.0)
    new_features["annualized_funding_velocity_usd_m"] = (funding_m / lifespans).round(4)

    # ==========================================
    # LAYER 2: MISSINGNESS SEMANTICS & SCHEMA
    # ==========================================
    print("3. Layer 2: Computing Missingness Semantics & Schema Versions...")
    
    # Identify question columns
    mean_q_cols = [c for c in df.columns if c.startswith("mean_")]
    
    # Overall data completeness (0.0 - 1.0)
    new_features["overall_data_completeness_pct"] = (df[mean_q_cols].notna().mean(axis=1)).round(3)
    
    # Category level missingness
    for cat_prefix in ["BC", "IS", "PMF", "M", "TP", "F", "L", "T", "ES", "IP"]:
        cat_cols = [c for c in mean_q_cols if f"_{cat_prefix}_" in c]
        if cat_cols:
            new_features[f"missingness_rate_{cat_prefix.lower()}"] = (df[cat_cols].isna().mean(axis=1)).round(3)

    # Schema version tag
    new_features["rubric_schema_generation"] = np.where(
        cohort_years <= 2018, "V1_Legacy_2016_2018", "V2_Modern_2019_2024"
    )

    # ==========================================
    # LAYER 3: POWER-LAW & TWO-STAGE TARGETS
    # ==========================================
    print("4. Layer 3: Engineering Power-Law & Two-Stage ML Targets...")
    
    funding_clean_usd = funding_m * 1_000_000.0
    new_features["target_funding_usd_clean"] = funding_clean_usd
    new_features["target_log10_funding_usd"] = np.log10(1.0 + funding_clean_usd).round(3)
    new_features["target_stage1_funded_binary"] = (funding_clean_usd > 0).astype(int)
    new_features["target_raised_1m_plus"] = (funding_clean_usd >= 1_000_000.0).astype(int)
    new_features["target_raised_5m_plus"] = (funding_clean_usd >= 5_000_000.0).astype(int)

    # Clean Binary Survival Target
    status_cols = [c for c in df.columns if "Still Alive?" in c or "From 2026 onwards" in c or "Status as of" in c]
    if status_cols:
        stat_col = status_cols[0]
        raw_stat = df[stat_col].astype(str).str.strip().str.upper()
        survival_target = np.where(
            raw_stat.str.startswith("Y") | raw_stat.str.startswith("A"), 1.0,
            np.where(raw_stat.str.startswith("N"), 0.0, np.nan)
        )
        new_features["target_survival_binary"] = survival_target
    else:
        new_features["target_survival_binary"] = np.nan

    # ==========================================
    # LAYER 4: 5 ORTHOGONAL LATENT FACTORS (0-100)
    # ==========================================
    print("5. Layer 4: Synthesizing 5 Orthogonal Latent Factors...")

    def get_val(col_name, default=0.0):
        if col_name in df.columns:
            return pd.to_numeric(df[col_name], errors="coerce").fillna(default)
        return pd.Series(default, index=df.index)

    # 1. Tech Defensibility (TRL 40%, Lab validation 30%, Patents 20%, Citations 10%)
    trl_score = get_val("mean_TP_Q7") * 100.0
    lab_val_score = get_val("mean_TP_Q12") * 100.0
    patent_score = get_val("mean_TP_Q5") * 100.0
    cite_score = get_val("mean_TP_Q1") * 100.0
    factor_tech = (0.40 * trl_score + 0.30 * lab_val_score + 0.20 * patent_score + 0.10 * cite_score).clip(0, 100)
    new_features["Factor_TechDefensibility"] = factor_tech.round(1)

    # 2. Commercial Traction (Interviews Tier 40%, Pilots/LOIs 35%, Sales data 25%)
    interview_tier = df.get("customer_interview_tier", "0-3_Interviews")
    interview_score = np.where(
        interview_tier == "10+_Interviews", 100.0,
        np.where(interview_tier == "6-9_Interviews", 75.0,
        np.where(interview_tier == "4-5_Interviews", 50.0, 15.0))
    )
    pilot_score = get_val("mean_ES_Q11") * 100.0
    sales_score = get_val("mean_F_Q25") * 100.0
    factor_traction = (0.40 * interview_score + 0.35 * pilot_score + 0.25 * sales_score).clip(0, 100)
    new_features["Factor_CommercialTraction"] = factor_traction.round(1)

    # 3. Financial Fluency (3-5yr Projections 35%, First Revenue Timeline 35%, Budget detail 30%)
    proj_score = get_val("mean_F_Q27") * 100.0
    rev_date_score = get_val("mean_IP_Q55") * 100.0
    budget_score = get_val("mean_F_Q3") * 100.0
    factor_finance = (0.35 * proj_score + 0.35 * rev_date_score + 0.30 * budget_score).clip(0, 100)
    new_features["Factor_FinancialFluency"] = factor_finance.round(1)

    # 4. Market Structure (TAM Sizing 40%, Distribution 30%, Competitors 30%)
    tam_score = get_val("mean_M_Q1") * 100.0
    dist_score = get_val("mean_M_Q2") * 100.0
    comp_score = get_val("mean_TP_Q4") * 100.0
    factor_market = (0.40 * tam_score + 0.30 * dist_score + 0.30 * comp_score).clip(0, 100)
    new_features["Factor_MarketStructure"] = factor_market.round(1)

    # 5. Impact & Regulatory (SDGs 35%, Quantifiable Emissions 35%, Compliance 30%)
    sdg_score = get_val("mean_IS_Q1") * 100.0
    emiss_score = get_val("mean_IS_Q4") * 100.0
    reg_score = get_val("IS_Q7_resolved_score") * 100.0
    factor_impact = (0.35 * sdg_score + 0.35 * emiss_score + 0.30 * reg_score).clip(0, 100)
    new_features["Factor_ImpactRegulatory"] = factor_impact.round(1)

    # Composite Balanced Index (0-100)
    composite_index = (
        0.30 * factor_tech + 
        0.25 * factor_traction + 
        0.20 * factor_finance + 
        0.15 * factor_market + 
        0.10 * factor_impact
    ).round(1)
    new_features["Composite_Execution_Index"] = composite_index

    # ==========================================
    # LAYER 5: SECTOR BASELINES & SHAP DELTAS
    # ==========================================
    print("6. Layer 5: Computing Sector Baseline Benchmarks & Deltas...")
    
    # Standardize Sector Names
    raw_ind = df.iloc[:, 2].astype(str).str.lower()
    
    def clean_sector(s):
        if any(k in s for k in ["energy", "solar", "battery", "storage", "power", "grid"]):
            return "Clean Energy & Storage"
        elif any(k in s for k in ["agri", "water", "waste", "food", "bio"]):
            return "Agriculture, Water & Waste"
        elif any(k in s for k in ["transport", "mobility", "vehicle", "ev", "auto"]):
            return "Transportation & Mobility"
        elif any(k in s for k in ["material", "chemical", "nano"]):
            return "Advanced Materials & Chemicals"
        elif any(k in s for k in ["build", "efficiency", "hvac", "lighting"]):
            return "Green Buildings & Efficiency"
        elif any(k in s for k in ["ict", "software", "data", "sensor", "iot"]):
            return "Software & Clean ICT"
        return "Clean Energy & Storage" # predominant default

    sector_clean = raw_ind.apply(clean_sector)
    new_features["standardized_sector"] = sector_clean

    # Combine all features into temporary df to compute sector medians
    feature_df = pd.DataFrame(new_features, index=df.index)
    
    factors = [
        "Factor_TechDefensibility", "Factor_CommercialTraction", 
        "Factor_FinancialFluency", "Factor_MarketStructure", 
        "Factor_ImpactRegulatory", "Composite_Execution_Index"
    ]
    
    sector_baselines = feature_df.groupby("standardized_sector")[factors].median().round(1)
    sector_summary_path = os.path.join(proc_dir, "sector_baselines_summary.csv")
    sector_baselines.to_csv(sector_summary_path)
    print("Sector Baselines Table:")
    print(sector_baselines)

    # Compute deltas against sector benchmark
    for factor in factors:
        medians_mapped = feature_df["standardized_sector"].map(sector_baselines[factor])
        delta_col = f"delta_vs_sector_{factor.lower().replace('factor_', '')}"
        feature_df[delta_col] = (feature_df[factor] - medians_mapped).round(1)

    # ==========================================
    # ASSEMBLE FINAL ML FEATURE MATRIX
    # ==========================================
    print("7. Assembling Master ML Feature Matrix...")
    # Concat raw identity columns with all newly engineered features and resolved features
    id_cols = ["company_id", "Company Name (original)", "clean_name", "Year", "Founder"]
    core_id_df = df[[c for c in id_cols if c in df.columns]]
    
    # Retain all resolved bools and conflicts
    resolved_cols = [c for c in df.columns if c.endswith("_resolved_bool") or c.endswith("_conflict_flag") or c.endswith("_resolved_score")]
    resolved_df = df[resolved_cols]
    
    # Merge everything
    final_ml_matrix = pd.concat([core_id_df, feature_df, resolved_df], axis=1)

    out_csv = os.path.join(proc_dir, "master_ml_feature_matrix.csv")
    final_ml_matrix.to_csv(out_csv, index=False)
    
    print(f"\n=======================================================")
    print(f"SUCCESS: Generated Master ML Feature Matrix!")
    print(f"Total Companies: {len(final_ml_matrix)}")
    print(f"Total ML Features: {len(final_ml_matrix.columns)}")
    print(f"Saved to: {out_csv}")
    print(f"=======================================================")

if __name__ == '__main__':
    run_evolution()
