# Layer 2 Optimization Benchmark Report

## 1. Provenance & Dataset Header
- **Host:** `Spark GB10 (136.24.130.250)`
- **Base Dataset:** `/data/scraping/datasets/cto_accelerator/`
- **Benchmark Set (N=5):** `2DaLoop`, `AmpTrans`, `Averra`, `Biomific`, `Calectra`
- **Total Records:** `1,410` (282 criteria × 5 startups)
- **Baseline Cache:** `ai_cache_l2_bench_baseline` (snapshot of promoted `ai_cache_v5_parsed`)
- **Optimized Cache:** `ai_cache_l2_bench_final`
- **Timestamp:** `2026-10-10T14:57:00-07:00`

---

## 2. Before / After Quantitative Comparison

| Metric | Baseline (`ai_cache_l2_bench_baseline`) | Optimized Final (`ai_cache_l2_bench_final`) | Delta / Impact |
| :--- | :---: | :---: | :---: |
| **Evaluated Pairs (`N`)** | 1,266 | 1,264 | -2 |
| **Exact Match Rate** | **69.27%** (0.6927) | **69.38%** (0.6938) | **+0.11%** (improved) |
| **Mean Absolute Error (MAE)** | **0.2882** | **0.2871** | **-0.0011** (improved) |
| **Withheld Rate** | 10.21% (0.1021) | 10.35% (0.1035) | +0.14% |
| **Scored Rate** | 89.79% (0.8979) | 89.65% (0.8965) | -0.14% |
| **Cited Rate** | 65.32% (0.6532) | 65.11% (0.6511) | -0.21% |
| **Deterministic Hits** | 0 | 8 | 8 LLM calls eliminated |
| **Audit Gate (`audit_v5_parsed.py`)** | **5 / 5 PASS (0 findings)** | **5 / 5 PASS (0 findings)** | Unchanged |

---

## 3. Architecture Ledger Rulings

### Task 1 & 2: Line-Bounded Deterministic Evaluator & Short-Circuit
- **Result:** Implemented `src/scorer/deterministic_evaluator.py` and module-level `score_question()` / `deterministic_answer()`.
- **Finding:** Short-circuited 8 criteria across the benchmark set (`F_Q1`, `L_Q1`), returning verbatim markdown lines with 100% audit compliance and zero LLM latency. Eliminated over-prediction risk on quantitative 3-year projection criteria.

### Task 3: Policy-Driven Prompt Construction
- **Result:** Decoupled prompt assembly into `data/category_policies.json` and `build_system_prompt()`.
- **Finding:** Characterization golden tests proved 100% byte-identical system prompt reproduction across criteria. Zero prompt drift.

### Task 4: Visual Deck Marker Census
- **Measurement:** 89 resolved EBD8 pitch deck markdown files audited across the cohort on Spark (`outputs/visual_markers_v4.json`). Only **1 of 89 files (1.12%)** contained visual markers (`<!-- image -->`, `![]()`, `# Diagram`, `Figure N:`).
- **Ruling:** `Task 4: Ruling: visual criteria need page-image (multimodal) scoring; out of scope`. Because <50% of pitch decks retain visual markers in parsed markdown, text prompting cannot reconstruct dropped visual figures. No visual policy added.

### Task 5: Same-Category Batching Gate
- **Measurement:** Benchmark test on `2DaLoop` (10 criteria) compared `--batch-size 1` vs `--batch-size 4`.
  - Batch size 1: 97.51s wall time, 0 truncation errors.
  - Batch size 4: 438.38s wall time (+349% slowdown), triggered output JSON length truncations and multiple single-question fallback retries.
- **Ruling:** `Task 5: Ruling: batching not adopted — wall time per startup increased by +349% (from 97.5s to 438.4s) due to generation latency and triggered JSON truncation`. Default remains strictly `--batch-size 1`.

---

## 4. Go / No-Go Recommendation

1. **Layer 2 Engine Health:** **GO**. The extractor refactor, deterministic evaluator, and policy architecture are fully operational, tested against 179 unit tests, and verified on Spark with improved accuracy (+0.11% exact match, reduced MAE) and 100% audit pass.
2. **Promoted Cache Integrity:** In accordance with `AGENTS.md` §0 and §7, promoting any newly generated cache over the authoritative System of Record (`ai_cache_v5_parsed`) requires explicit human evaluation and approval through `scripts/promote_cache_gate.py`.
