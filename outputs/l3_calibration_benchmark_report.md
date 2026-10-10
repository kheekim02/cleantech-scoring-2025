# Diligence Accuracy & Discrepancy Gap Closure Benchmark Report

## 1. Provenance & Dataset Header
- **Host:** `Spark GB10 (136.24.130.250)`
- **Base Dataset Directory:** `/data/scraping/datasets/cto_accelerator/`
- **Active Startup Allowlist:** `active_startup_allowlist.json` (92 active startups)
- **Master Rubric:** `master_282_rubric.json` (Frozen 282 criteria)
- **Source Cache (Authoritative SoR):** `ai_cache_promoted -> ai_cache_v5_parsed` (25,944 records)
- **Candidate Cache:** `ai_cache_l3_candidate` (25,944 records)
- **Human Benchmark Ground Truth:** `outputs/human_scores.json` (9,708 evaluated criteria pairs)
- **Timestamp:** `2026-10-10T15:54:00-07:00`

---

## 2. Track A: Document Routing Enhancement Results

### Deliverable Coverage Across Cohort (N=92 Startups)

| Evaluation Category | Baseline Primary Coverage | Enhanced Primary (`docling_ingestion.py`) | Fallback Synthesized (`CAT_FALLBACK_SOURCES`) | Total Covered | Uncovered / Missing |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **PMF** (Product Market Fit) | 73 (79.3%) | **88 (95.7%)** | **4 (4.3%)** | **92 / 92 (100%)** | **0** |
| **M** (Marketing & Customers) | 81 (88.0%) | **89 (96.7%)** | **3 (3.3%)** | **92 / 92 (100%)** | **0** |
| **BC** (Business Canvas) | 62 (67.4%) | **91 (98.9%)** | **1 (1.1%)** | **92 / 92 (100%)** | **0** |
| **IS** (Impact Strategy / Exec Summary) | 86 (93.5%) | **91 (98.9%)** | **0** | **91 / 92 (98.9%)** | **1** |

**Key Finding:** Expanding classification regexes (`M1`, `M3`, `M4`, `EBD3`) and adding multi-source fallback synthesis (`EBD1` Canvas + `EBD8` Pitch Deck) completely eliminated deliverable blindness for `PMF`, `M`, and `BC` (0 missing startups across the entire 92-startup cohort).

---

## 3. Track B: Multimodal Visual Ingestion Results (`IP_Q7`, `PMF_Q24`)

- **PyMuPDF Deck Inspector (`src/scorer/visual_deck_inspector.py`):**
  - Evaluated all 92 slide decks recursively in `raw/<sid>/**/*.pdf`.
  - Identified **167 visual diagram / logo candidates** across the cohort.
- **Audit Gate G1.1 Constraint:**
  - Independent citation audit flagged synthetic English citation strings (e.g. `"Slide 1 displays high-resolution logo asset..."`) under **Gate G1.1: citation not verbatim in primary markdown**.
  - **Architectural Ruling:** In text-grounded diligence systems, any non-zero citation must be a verbatim substring in the primary markdown document. For visual criteria, citations must extract verbatim heading/caption lines from the slide markdown rather than synthetic narrative sentences.

---

## 4. Track C: Layer 3 Calibrated Score Mapping Analysis

### Quantitative Ground-Truth Analysis on 5,025 Model Zero Scores:
- When AI scored `0.0`: Human judges also scored `0.0` in **66.6%** of cases (3,347 / 5,025 pairs).
- When AI scored `1.0`: Human judges also scored `1.0` in **79.6%** of cases (3,383 / 4,250 pairs).
- **Post-Hoc Score Inflation Impact:**
  - Flipping model `0.0` scores to `0.5` degraded exact match from **71.17% down to 69.54%** and worsened MAE from **0.2607 to 0.2709**.
  - Created 692 **Gate G2.3 violations** (absence language in rationale combined with positive score >= 0.5).
- **Architectural Ruling:** Diligence accuracy cannot be improved through blind post-hoc score bumps on absence rationales. True calibration must occur through primary context hydration (Track A), where the LLM evaluates the newly routed documents directly with verbatim evidence.

---

## 5. Promotion Gate Ruling & System of Record Invariant

1. **Candidate Cache Disposition:** `ai_cache_l3_candidate` is **NOT promoted**.
2. **Promoted SoR Integrity:** `ai_cache_promoted -> ai_cache_v5_parsed` remains the authoritative, golden System of Record.
3. **Production State:** Zero writes to Supabase PostgreSQL or human scoring schemas.
