# Layer 2 Deterministic Sweep Report (Cohort-Wide N=92)

## 1. Provenance & Dataset Header
- **Host:** `Spark GB10 (136.24.130.250)`
- **Base Dataset Directory:** `/data/scraping/datasets/cto_accelerator/`
- **Active Startup Allowlist:** `active_startup_allowlist.json` (92 active CleanTech Open startups)
- **Master Rubric:** `master_282_rubric.json` (Frozen 282 criteria)
- **Source Cache (Golden SoR):** `ai_cache_promoted -> ai_cache_v5_parsed` (25,944 records)
- **Candidate Cache:** `ai_cache_l2_deterministic_candidate` (25,944 records)
- **Execution Script:** `scripts/apply_deterministic_overrides.py`
- **Timestamp:** `2026-10-10T15:35:00-07:00`

---

## 2. Execution Summary & Quantitative Comparison

The superior alternative executed line-bounded deterministic criteria evaluation purely in memory across all 92 startups from `parsed_clean_v4` markdown without invoking LLM endpoints.

- **Execution Runtime:** **1.8 seconds wall time** on Spark (vs. estimated **69.3 GPU hours** for a full LLM re-run across 25,576 criteria queries, yielding a **>138,000x speedup** and zero GPU allocation).
- **Startups Evaluated:** 92 / 92 (100% complete)
- **Total Deterministic Overrides Applied:** **100** across 75 startups
  - `F_Q1`: 64 overrides
  - `L_Q1`: 32 overrides
  - `F_Q7`: 2 overrides
  - `L_Q14`: 2 overrides

### Human Reviews Benchmark (Read-Only `outputs/human_scores.json`)

| Metric | Promoted SoR (`ai_cache_promoted`) | Candidate (`ai_cache_l2_deterministic_candidate`) | Delta |
| :--- | :---: | :---: | :---: |
| **Total Criteria Records** | 25,944 | 25,944 | 0 |
| **Evaluated Pairs (`N`)** | 9,708 | 9,710 | +2 pairs |
| **Exact Match Rate** | **71.17%** (0.71168) | **71.15%** (0.71153) | **-0.015%** |
| **Mean Absolute Error (MAE)** | **0.2607** (0.26067) | **0.2608** (0.26082) | **+0.00015** |
| **Withheld Rate** | 15.02% | 15.00% | -0.02% |
| **Scored Rate** | 84.98% | 85.00% | +0.02% |
| **Cited Rate** | 62.85% | 62.88% | +0.03% |

---

## 3. Independent Citation & Quality Audit Gate (`audit_citations_independent.py`)

| Gate Check | Promoted SoR (`ai_cache_promoted`) | Candidate (`ai_cache_l2_deterministic_candidate`) | Verdict |
| :--- | :---: | :---: | :---: |
| **Cohort Status** | **GREEN** | **RED** | **CANDIDATE REJECTED** |
| **HARD Violations** | **0** | **6** | +6 HARD violations |
| **G3.1 (Clone Citation Clusters)** | 0 | 6 clusters (G3.1 failure) | Cross-company duplicate lines |
| **G1.4 / G2.1 / G3.3 (Soft)** | 11,055 | 11,161 | +106 soft findings |

### Root Cause Analysis of G3.1 Failure:
When the deterministic regex extracted verbatim single markdown lines matching table headers (e.g. `Year 1 revenue ... Year 2 revenue ... Year 3 revenue` in `EBD5` or `Delaware C Corporation` in `M7`), the extracted string was identical across companies that shared the same template structure. Gate `G3.1` strictly prohibits duplicate verbatim citations across distinct companies to prevent template scaffolding leaks. In contrast, the promoted SoR extracts startup-specific row data and figures, which passed `G3.1` cleanly.

---

## 4. Master Rubric Alignment Findings

Detailed inspection of the 100 overrides against the frozen `master_282_rubric.json` revealed:
1. **`L_Q1`:** Rubric defines `L_Q1` as *"Does the company have an intellectual property strategy?"*, whereas the regex in `deterministic_evaluator.py` matched corporate incorporation entities (`CORP_ENTITY_RE`). In `ai_cache_promoted`, `L_Q1` already possessed valid, startup-specific IP strategy citations.
2. **`F_Q7`:** Rubric defines `F_Q7` as *"Are revenue and expense projections identified as fixed, variable, or marginal?"*, whereas the regex in `deterministic_evaluator.py` matched breakeven statements (`BREAKEVEN_RE`), leading to a mismatch with human reviews (human score: 0.00 vs overridden 1.00).
3. **`L_Q14`:** Rubric defines `L_Q14` as *"Is there any open-source code in the product?"*, whereas the regex in `deterministic_evaluator.py` matched patent numbers (`PATENT_RE`).

---

## 5. Architectural Ruling & System of Record Invariant

1. **Candidate Promotion Rejection:** In strict adherence to `AGENTS.md` §0, §5, and §7, `ai_cache_l2_deterministic_candidate` **FAILS the promotion gate** due to:
   - 6 HARD `G3.1` audit violations (cloned template citations).
   - Negative delta on human agreement (-0.015% exact match).
2. **Authoritative Golden Cache Maintained:** `ai_cache_promoted -> ai_cache_v5_parsed` remains the untouched, canonical System of Record.
3. **Zero Supabase Writes:** Verification confirms zero writes were performed to Supabase PostgreSQL or human scoring tables.
