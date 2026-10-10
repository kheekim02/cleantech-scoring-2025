#!/usr/bin/env python3
"""
Phase 1: Exhaustive Inter-Rater Reliability (IRR) & Scorer Consistency Audit
=============================================================================
CleanTech Open Diligence Engine — 283 question pairs, 997 startups, 9 cohorts.

Computes per-question:
  - Exact match agreement %
  - Tolerance agreement (±0.1 and ±0.25 on normalized 0–1 scale)
  - Cohen's Kappa (unweighted, linear-weighted, quadratic-weighted)
  - ICC(2,1) — two-way random, single measures
  - Score variance decomposition (between-startup vs. between-rater)
  - Mean absolute difference (native and normalized)

Segments by: category, cohort year, archetype, objectivity flag.
Statistical tests: Mann-Whitney U, Kruskal-Wallis.
"""

import pandas as pd
import numpy as np
import re
import json
import warnings
from pathlib import Path
from sklearn.metrics import cohen_kappa_score
from scipy.stats import mannwhitneyu, kruskal

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs" / "phase1_irr"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Load datasets
# ---------------------------------------------------------------------------
def load_data():
    df = pd.read_csv(ROOT / "data/processed/master_raw_startup_dataset.csv", low_memory=False)
    qm = pd.read_csv(ROOT / "data/processed/master_questions_metadata.csv", low_memory=False)
    with open(ROOT / "master_282_rubric.json") as f:
        rubric = json.load(f)
    return df, qm, rubric


# ---------------------------------------------------------------------------
# 2. Build question-pair registry from column names
# ---------------------------------------------------------------------------
COL_PAT = re.compile(r"^(\w+)_Scorer_1_Q(\d+)$")


def build_pair_registry(df: pd.DataFrame) -> list[dict]:
    """Return list of dicts with cat, qnum, col_s1, col_s2, q_id."""
    pairs = []
    for col in df.columns:
        m = COL_PAT.match(col)
        if not m:
            continue
        cat, qnum = m.group(1), int(m.group(2))
        col_s2 = f"{cat}_Scorer_2_Q{qnum}"
        if col_s2 in df.columns:
            pairs.append({
                "cat": cat,
                "qnum": qnum,
                "q_id": f"{cat}_Q{qnum}",
                "col_s1": col,
                "col_s2": col_s2,
            })
    return pairs


# ---------------------------------------------------------------------------
# 3. Map question metadata onto pairs
# ---------------------------------------------------------------------------
CAT_SECTION_MAP = {
    "1. Business Canvas": "BC",
    "2. Impact/ Sustainability": "ES",
    "3. Product/ Market Fit": "PMF",
    "4. Markets": "M",
    "5. Tech and Product": "TP",
    "6. Financials": "F",
    "7. Legal": "L",
    "8. Team": "T",
    "9. Executive Summary": "IS",
    "10. Investor Pitch": "IP",
}


def enrich_pairs(pairs: list[dict], qm: pd.DataFrame) -> pd.DataFrame:
    """Attach is_objective, archetype from questions metadata."""
    # Build lookup: cat_code + qnum → metadata row
    qm = qm.copy()
    qm["cat_code"] = qm["category_section"].map(CAT_SECTION_MAP)
    qm["qnum"] = qm["question_number_in_cat"].astype(int)
    qm_lookup = qm.set_index(["cat_code", "qnum"])

    for p in pairs:
        key = (p["cat"], p["qnum"])
        if key in qm_lookup.index:
            row = qm_lookup.loc[key]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            p["is_objective"] = int(row.get("is_objective", -1))
            p["archetype"] = row.get("archetype", "UNKNOWN")
            p["question_text"] = row.get("question_text", "")
        else:
            p["is_objective"] = -1
            p["archetype"] = "UNMAPPED"
            p["question_text"] = ""

    return pd.DataFrame(pairs)


# ---------------------------------------------------------------------------
# 4. ICC(2,1) — two-way random effects, single measures, manual
# ---------------------------------------------------------------------------
def icc_2_1(r1: np.ndarray, r2: np.ndarray) -> float:
    """
    ICC(2,1) for exactly 2 raters.
    Two-way random, single measures, absolute agreement.
    """
    n = len(r1)
    if n < 3:
        return np.nan
    k = 2
    # Stack: n×k matrix
    X = np.column_stack([r1, r2])
    grand_mean = X.mean()
    row_means = X.mean(axis=1)
    col_means = X.mean(axis=0)

    # Sum of squares
    SS_total = np.sum((X - grand_mean) ** 2)
    SS_rows = k * np.sum((row_means - grand_mean) ** 2)
    SS_cols = n * np.sum((col_means - grand_mean) ** 2)
    SS_error = SS_total - SS_rows - SS_cols

    # Mean squares
    df_rows = n - 1
    df_cols = k - 1
    df_error = (n - 1) * (k - 1)

    MS_rows = SS_rows / df_rows if df_rows > 0 else 0
    MS_cols = SS_cols / df_cols if df_cols > 0 else 0
    MS_error = SS_error / df_error if df_error > 0 else 0

    # ICC(2,1) formula
    denom = MS_rows + (k - 1) * MS_error + k * (MS_cols - MS_error) / n
    if denom == 0:
        return np.nan
    return (MS_rows - MS_error) / denom


# ---------------------------------------------------------------------------
# 5. Per-question IRR metrics
# ---------------------------------------------------------------------------
def compute_question_irr(
    df: pd.DataFrame, pair: dict
) -> dict:
    """Compute all IRR metrics for a single question pair."""
    col_s1, col_s2 = pair["col_s1"], pair["col_s2"]

    # Extract and coerce to numeric
    r1 = pd.to_numeric(df[col_s1], errors="coerce")
    r2 = pd.to_numeric(df[col_s2], errors="coerce")

    # Drop rows where either is NaN
    mask = r1.notna() & r2.notna()
    r1, r2 = r1[mask].values, r2[mask].values
    n = len(r1)

    result = {
        "q_id": pair["q_id"],
        "cat": pair["cat"],
        "qnum": pair["qnum"],
        "n_pairs": n,
    }

    if n < 10:
        # Insufficient data
        for k in [
            "exact_agree", "tol_01_agree", "tol_025_agree",
            "kappa_unweighted", "kappa_linear", "kappa_quadratic",
            "icc_2_1", "mad_native", "mad_norm",
            "var_between_startup", "var_between_rater", "var_ratio",
            "r1_mean", "r2_mean", "rater_bias", "scale_max",
            "floor_pct", "ceiling_pct",
        ]:
            result[k] = np.nan
        return result

    # Scale properties
    all_vals = np.concatenate([r1, r2])
    scale_max = np.nanmax(all_vals)
    scale_min = np.nanmin(all_vals)
    result["scale_max"] = scale_max
    result["scale_min"] = scale_min

    # Normalize to 0–1
    scale_range = scale_max - scale_min
    if scale_range > 0:
        r1_norm = (r1 - scale_min) / scale_range
        r2_norm = (r2 - scale_min) / scale_range
    else:
        r1_norm = np.zeros_like(r1)
        r2_norm = np.zeros_like(r2)

    # --- Agreement metrics ---
    result["exact_agree"] = np.mean(r1 == r2)

    abs_diff_norm = np.abs(r1_norm - r2_norm)
    result["tol_01_agree"] = np.mean(abs_diff_norm <= 0.1)
    result["tol_025_agree"] = np.mean(abs_diff_norm <= 0.25)

    # --- Mean absolute difference ---
    result["mad_native"] = np.mean(np.abs(r1 - r2))
    result["mad_norm"] = np.mean(abs_diff_norm)

    # --- Cohen's Kappa ---
    # Discretize to native unique values (preserve precision)
    try:
        result["kappa_unweighted"] = cohen_kappa_score(r1, r2)
    except Exception:
        result["kappa_unweighted"] = np.nan

    try:
        result["kappa_linear"] = cohen_kappa_score(r1, r2, weights="linear")
    except Exception:
        result["kappa_linear"] = np.nan

    try:
        result["kappa_quadratic"] = cohen_kappa_score(r1, r2, weights="quadratic")
    except Exception:
        result["kappa_quadratic"] = np.nan

    # --- ICC(2,1) ---
    result["icc_2_1"] = icc_2_1(r1, r2)

    # --- Variance decomposition ---
    # Model: score_ij = μ + α_i (startup) + β_j (rater) + ε_ij
    mean_per_startup = (r1 + r2) / 2.0
    diff_per_startup = r1 - r2

    result["var_between_startup"] = np.var(mean_per_startup, ddof=1)
    result["var_between_rater"] = np.var(diff_per_startup, ddof=1) / 4.0  # Var(β) ≈ Var(d)/4

    total_var = result["var_between_startup"] + result["var_between_rater"]
    result["var_ratio"] = (
        result["var_between_startup"] / total_var if total_var > 0 else np.nan
    )

    # --- Rater bias ---
    result["r1_mean"] = np.mean(r1)
    result["r2_mean"] = np.mean(r2)
    result["rater_bias"] = np.mean(r1) - np.mean(r2)

    # --- Floor / ceiling effects ---
    result["floor_pct"] = np.mean(all_vals == scale_min)
    result["ceiling_pct"] = np.mean(all_vals == scale_max)

    return result


# ---------------------------------------------------------------------------
# 6. Temporal IRR segmentation (by cohort year)
# ---------------------------------------------------------------------------
def compute_temporal_irr(
    df: pd.DataFrame, pairs: list[dict]
) -> pd.DataFrame:
    """Compute category-level IRR metrics by cohort year."""
    years = sorted(df["Year"].dropna().unique())
    records = []

    for year in years:
        df_year = df[df["Year"] == year]
        if len(df_year) < 10:
            continue

        # Group by category
        cat_groups: dict[str, list[dict]] = {}
        for p in pairs:
            cat_groups.setdefault(p["cat"], []).append(p)

        for cat, cat_pairs in cat_groups.items():
            exact_agrees = []
            kappas = []
            iccs = []
            mads = []

            for p in cat_pairs:
                r1 = pd.to_numeric(df_year[p["col_s1"]], errors="coerce")
                r2 = pd.to_numeric(df_year[p["col_s2"]], errors="coerce")
                mask = r1.notna() & r2.notna()
                r1v, r2v = r1[mask].values, r2[mask].values
                if len(r1v) < 5:
                    continue
                exact_agrees.append(np.mean(r1v == r2v))
                mads.append(np.mean(np.abs(r1v - r2v)))
                try:
                    kappas.append(cohen_kappa_score(r1v, r2v, weights="linear"))
                except Exception:
                    pass
                iccs.append(icc_2_1(r1v, r2v))

            if not exact_agrees:
                continue

            records.append({
                "year": int(year),
                "cat": cat,
                "n_questions": len(exact_agrees),
                "mean_exact_agree": np.nanmean(exact_agrees),
                "mean_kappa_linear": np.nanmean(kappas) if kappas else np.nan,
                "mean_icc": np.nanmean(iccs),
                "mean_mad": np.nanmean(mads),
            })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# 7. Category-level aggregation
# ---------------------------------------------------------------------------
def aggregate_by_category(irr_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-question IRR to category-level summary."""
    agg = irr_df.groupby("cat").agg(
        n_questions=("q_id", "count"),
        mean_n_pairs=("n_pairs", "mean"),
        mean_exact_agree=("exact_agree", "mean"),
        median_exact_agree=("exact_agree", "median"),
        std_exact_agree=("exact_agree", "std"),
        mean_tol01=("tol_01_agree", "mean"),
        mean_tol025=("tol_025_agree", "mean"),
        mean_kappa_uw=("kappa_unweighted", "mean"),
        mean_kappa_lin=("kappa_linear", "mean"),
        mean_kappa_quad=("kappa_quadratic", "mean"),
        median_kappa_lin=("kappa_linear", "median"),
        mean_icc=("icc_2_1", "mean"),
        median_icc=("icc_2_1", "median"),
        mean_mad_norm=("mad_norm", "mean"),
        mean_var_ratio=("var_ratio", "mean"),
        mean_floor_pct=("floor_pct", "mean"),
        mean_ceiling_pct=("ceiling_pct", "mean"),
        mean_rater_bias=("rater_bias", "mean"),
    ).reset_index()
    return agg


# ---------------------------------------------------------------------------
# 8. Aggregate by archetype and objectivity
# ---------------------------------------------------------------------------
def aggregate_by_taxonomy(irr_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate by archetype and by is_objective flag."""
    by_archetype = irr_df.groupby("archetype").agg(
        n_questions=("q_id", "count"),
        mean_exact_agree=("exact_agree", "mean"),
        mean_kappa_lin=("kappa_linear", "mean"),
        mean_icc=("icc_2_1", "mean"),
        mean_mad_norm=("mad_norm", "mean"),
        mean_var_ratio=("var_ratio", "mean"),
    ).reset_index()

    by_obj = irr_df[irr_df["is_objective"] >= 0].groupby("is_objective").agg(
        n_questions=("q_id", "count"),
        mean_exact_agree=("exact_agree", "mean"),
        median_exact_agree=("exact_agree", "median"),
        std_exact_agree=("exact_agree", "std"),
        mean_kappa_lin=("kappa_linear", "mean"),
        median_kappa_lin=("kappa_linear", "median"),
        mean_icc=("icc_2_1", "mean"),
        mean_mad_norm=("mad_norm", "mean"),
        mean_var_ratio=("var_ratio", "mean"),
    ).reset_index()
    by_obj["label"] = by_obj["is_objective"].map({0: "Subjective", 1: "Objective"})

    return by_archetype, by_obj


# ---------------------------------------------------------------------------
# 9. Statistical hypothesis tests
# ---------------------------------------------------------------------------
def run_statistical_tests(irr_df: pd.DataFrame) -> dict:
    """Mann-Whitney U, Kruskal-Wallis on agreement by objectivity and category."""
    tests = {}

    # Filter to questions with valid metadata
    valid = irr_df[irr_df["is_objective"] >= 0].copy()
    obj = valid[valid["is_objective"] == 1]["exact_agree"].dropna()
    subj = valid[valid["is_objective"] == 0]["exact_agree"].dropna()

    if len(obj) >= 5 and len(subj) >= 5:
        stat, p = mannwhitneyu(obj, subj, alternative="greater")
        tests["mwu_exact_agree_obj_gt_subj"] = {"U": stat, "p": p, "n_obj": len(obj), "n_subj": len(subj)}

    # Same for kappa
    obj_k = valid[valid["is_objective"] == 1]["kappa_linear"].dropna()
    subj_k = valid[valid["is_objective"] == 0]["kappa_linear"].dropna()
    if len(obj_k) >= 5 and len(subj_k) >= 5:
        stat, p = mannwhitneyu(obj_k, subj_k, alternative="greater")
        tests["mwu_kappa_obj_gt_subj"] = {"U": stat, "p": p}

    # Same for ICC
    obj_i = valid[valid["is_objective"] == 1]["icc_2_1"].dropna()
    subj_i = valid[valid["is_objective"] == 0]["icc_2_1"].dropna()
    if len(obj_i) >= 5 and len(subj_i) >= 5:
        stat, p = mannwhitneyu(obj_i, subj_i, alternative="greater")
        tests["mwu_icc_obj_gt_subj"] = {"U": stat, "p": p}

    # Kruskal-Wallis across categories for exact_agree
    cat_groups = [
        g["exact_agree"].dropna().values
        for _, g in irr_df.groupby("cat")
        if len(g["exact_agree"].dropna()) >= 3
    ]
    if len(cat_groups) >= 3:
        stat, p = kruskal(*cat_groups)
        tests["kw_exact_agree_across_cats"] = {"H": stat, "p": p, "n_groups": len(cat_groups)}

    return tests


# ---------------------------------------------------------------------------
# 10. Leaderboards
# ---------------------------------------------------------------------------
def build_leaderboards(irr_df: pd.DataFrame, n: int = 15) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top-N highest and lowest agreement questions."""
    cols = ["q_id", "cat", "question_text", "archetype", "is_objective",
            "n_pairs", "exact_agree", "kappa_linear", "icc_2_1", "mad_norm",
            "floor_pct", "ceiling_pct", "rater_bias"]

    valid = irr_df.dropna(subset=["exact_agree"]).copy()
    best = valid.nlargest(n, "exact_agree")[cols]
    worst = valid.nsmallest(n, "exact_agree")[cols]
    return best, worst


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    print("=" * 80)
    print("PHASE 1: EXHAUSTIVE IRR AUDIT — CleanTech Open 2016–2024")
    print("=" * 80)

    # Load
    df, qm, rubric = load_data()
    print(f"\nDataset: {df.shape[0]} rows × {df.shape[1]} columns")

    # Build pair registry
    pairs = build_pair_registry(df)
    print(f"Scorer pairs identified: {len(pairs)}")

    # Enrich with metadata
    pairs_df = enrich_pairs(pairs, qm)
    pairs_list = pairs_df.to_dict("records")
    print(f"Pairs enriched with metadata: {len(pairs_list)}")
    print(f"  Mapped to rubric: {(pairs_df['is_objective'] >= 0).sum()}")
    print(f"  Unmapped: {(pairs_df['is_objective'] < 0).sum()}")

    # Compute per-question IRR
    print("\nComputing per-question IRR metrics...")
    irr_records = []
    for p in pairs_list:
        result = compute_question_irr(df, p)
        # Attach metadata
        result["is_objective"] = p["is_objective"]
        result["archetype"] = p["archetype"]
        result["question_text"] = p["question_text"]
        irr_records.append(result)

    irr_df = pd.DataFrame(irr_records)
    valid_qs = irr_df["exact_agree"].notna().sum()
    print(f"Questions with sufficient data (N≥10): {valid_qs}")

    # Save per-question results
    irr_df.to_csv(OUT_DIR / "per_question_irr.csv", index=False)
    print(f"  → Saved: {OUT_DIR / 'per_question_irr.csv'}")

    # --- Category aggregation ---
    print("\n" + "=" * 60)
    print("CATEGORY-LEVEL IRR SUMMARY")
    print("=" * 60)
    cat_agg = aggregate_by_category(irr_df)
    cat_agg.to_csv(OUT_DIR / "category_irr_summary.csv", index=False)

    # Print nicely
    display_cols = [
        "cat", "n_questions", "mean_n_pairs",
        "mean_exact_agree", "mean_tol025", "mean_kappa_lin",
        "median_kappa_lin", "mean_icc", "mean_mad_norm",
        "mean_floor_pct", "mean_ceiling_pct", "mean_rater_bias",
    ]
    print(cat_agg[display_cols].to_string(index=False, float_format="%.3f"))

    # --- Archetype / Objectivity aggregation ---
    print("\n" + "=" * 60)
    print("IRR BY QUESTION ARCHETYPE")
    print("=" * 60)
    by_archetype, by_obj = aggregate_by_taxonomy(irr_df)
    by_archetype.to_csv(OUT_DIR / "archetype_irr.csv", index=False)
    by_obj.to_csv(OUT_DIR / "objectivity_irr.csv", index=False)
    print(by_archetype.to_string(index=False, float_format="%.3f"))

    print("\n" + "=" * 60)
    print("IRR BY OBJECTIVITY FLAG")
    print("=" * 60)
    print(by_obj.to_string(index=False, float_format="%.3f"))

    # --- Statistical tests ---
    print("\n" + "=" * 60)
    print("STATISTICAL HYPOTHESIS TESTS")
    print("=" * 60)
    tests = run_statistical_tests(irr_df)
    for name, vals in tests.items():
        print(f"\n  {name}:")
        for k, v in vals.items():
            if isinstance(v, float):
                print(f"    {k}: {v:.6f}")
            else:
                print(f"    {k}: {v}")

    # --- Temporal drift ---
    print("\n" + "=" * 60)
    print("TEMPORAL IRR DRIFT (by cohort year)")
    print("=" * 60)
    temporal = compute_temporal_irr(df, pairs_list)
    temporal.to_csv(OUT_DIR / "temporal_irr.csv", index=False)

    # Show year-level average across all categories
    year_avg = temporal.groupby("year").agg(
        mean_exact_agree=("mean_exact_agree", "mean"),
        mean_kappa=("mean_kappa_linear", "mean"),
        mean_icc=("mean_icc", "mean"),
    ).reset_index()
    print(year_avg.to_string(index=False, float_format="%.3f"))

    # --- Leaderboards ---
    print("\n" + "=" * 60)
    print("TOP 15 HIGHEST AGREEMENT QUESTIONS")
    print("=" * 60)
    best, worst = build_leaderboards(irr_df, n=15)
    best.to_csv(OUT_DIR / "top15_highest_agreement.csv", index=False)
    worst.to_csv(OUT_DIR / "top15_lowest_agreement.csv", index=False)

    lb_cols = ["q_id", "archetype", "exact_agree", "kappa_linear", "icc_2_1", "mad_norm"]
    print(best[lb_cols].to_string(index=False, float_format="%.3f"))

    print("\n" + "=" * 60)
    print("TOP 15 LOWEST AGREEMENT QUESTIONS (Highest Disagreement)")
    print("=" * 60)
    print(worst[lb_cols].to_string(index=False, float_format="%.3f"))

    # --- Global summary ---
    print("\n" + "=" * 60)
    print("GLOBAL SUMMARY STATISTICS")
    print("=" * 60)
    valid_irr = irr_df.dropna(subset=["exact_agree"])
    print(f"  Total questions analyzed: {len(valid_irr)}")
    print(f"  Mean exact agreement: {valid_irr['exact_agree'].mean():.3f}")
    print(f"  Median exact agreement: {valid_irr['exact_agree'].median():.3f}")
    print(f"  Mean Kappa (linear): {valid_irr['kappa_linear'].mean():.3f}")
    print(f"  Median Kappa (linear): {valid_irr['kappa_linear'].median():.3f}")
    print(f"  Mean ICC(2,1): {valid_irr['icc_2_1'].mean():.3f}")
    print(f"  Median ICC(2,1): {valid_irr['icc_2_1'].median():.3f}")
    print(f"  Mean MAD (normalized): {valid_irr['mad_norm'].mean():.3f}")
    print(f"  Mean floor %: {valid_irr['floor_pct'].mean():.3f}")
    print(f"  Mean ceiling %: {valid_irr['ceiling_pct'].mean():.3f}")

    # Questions with near-zero mutual information (exact agree ≈ floor/ceiling compression)
    compressed = valid_irr[
        (valid_irr["floor_pct"] > 0.80) | (valid_irr["ceiling_pct"] > 0.80)
    ]
    print(f"\n  Questions with >80% floor/ceiling compression: {len(compressed)}")
    if len(compressed) > 0:
        print(compressed[["q_id", "floor_pct", "ceiling_pct", "exact_agree"]].to_string(index=False, float_format="%.3f"))

    # Zero-information questions (kappa undefined or near-zero with high agreement from compression)
    zero_info = valid_irr[
        (valid_irr["kappa_linear"].abs() < 0.05)
        & (valid_irr["exact_agree"] > 0.85)
    ]
    print(f"\n  Zero-information questions (|κ|<0.05 & agree>85%): {len(zero_info)}")
    if len(zero_info) > 0:
        print(zero_info[["q_id", "exact_agree", "kappa_linear", "floor_pct", "ceiling_pct"]].head(20).to_string(index=False, float_format="%.3f"))

    print("\n" + "=" * 80)
    print("Phase 1 complete. All outputs saved to:", OUT_DIR)
    print("=" * 80)


if __name__ == "__main__":
    main()
