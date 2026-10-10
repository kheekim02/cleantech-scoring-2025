# Task 0 Benchmark Discrepancy Analysis Report

## 1. Provenance & Dataset Header
- **Source Host:** `Spark 136.24.130.250`
- **Cache Directory:** `datasets/cto_accelerator/ai_cache_l2_bench_baseline`
- **Benchmark Startups (N=5):** `2DaLoop, AmpTrans, Averra, Biomific, Calectra`
- **Total Evaluated Records:** `1410`

## 2. Category Performance Summary
Categories ranked by exact match rate (lowest to highest):

| Category | Code | Evaluated Pairs | Exact Match % | MAE | Mean Bias (AI - Human) | Withheld % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| BC | `BC` | 17 | **47.06%** | 0.294 | 0.000 | 32.00% |
| M | `M` | 56 | **58.93%** | 0.411 | -0.196 | 6.67% |
| IS | `IS` | 159 | **64.15%** | 0.358 | -0.233 | 6.47% |
| IP | `IP` | 276 | **66.30%** | 0.337 | -0.272 | 4.83% |
| T | `T` | 119 | **68.07%** | 0.184 | +0.055 | 23.23% |
| PMF | `PMF` | 151 | **69.54%** | 0.305 | -0.199 | 11.18% |
| L | `L` | 231 | **71.00%** | 0.290 | -0.134 | 12.83% |
| TP | `TP` | 80 | **77.50%** | 0.181 | -0.077 | 0.00% |
| ES | `ES` | 45 | **77.78%** | 0.211 | -0.122 | 10.00% |
| F | `F` | 132 | **78.79%** | 0.212 | +0.091 | 8.97% |

## 3. Global Error Mode Distribution

| Error Mode | Occurrence Count | Percentage of Evaluated Pairs | Diagnosis |
| :--- | :---: | :---: | :--- |
| **Exact Match** | 877 | 62.20% | Exact score agreement within 1e-9 |
| **Over Prediction** | 86 | 6.10% | AI awarded 1.0 while human scored <= 0.25 (loose regex or hallucinations) |
| **Under Prediction** | 263 | 18.65% | AI awarded 0.0 while human scored >= 0.75 (overly strict gating or primary doc miss) |
| **Fractional Tier Mismatch** | 40 | 2.84% | Disagreement on intermediate tiers (e.g. 0.5 vs 0.75) |
| **Withheld** | 144 | 10.21% | Model safely withheld without guessing |

## 4. Top 15 Highest-Discrepancy Criteria
Specific rubric questions with the highest mean absolute error (MAE) across the benchmark cohort:

| Question ID | Category | Question Prompt Excerpt | Pairs | MAE | Mean Bias | Exact Match % |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| `PMF_Q24` | `PMF` | Startup has a logo that is discernible when billboard size. | 3 | **1.000** | -1.000 | 0.0% |
| `PMF_Q30` | `PMF` | Has the startup analyzed the reasons why customers use the compet... | 5 | **1.000** | -1.000 | 0.0% |
| `F_Q11` | `F` | Are revenue and expenses by project identified by source or line ... | 5 | **1.000** | +1.000 | 0.0% |
| `F_Q14` | `F` | Does the capital budget include revenue, expense, and market proj... | 3 | **1.000** | +1.000 | 0.0% |
| `IP_Q7` | `IP` | Is there a visual "model" depicting the problem? | 5 | **1.000** | -1.000 | 0.0% |
| `IP_Q20` | `IP` | Does the methodology combine quantitative rigor with qualitative ... | 5 | **1.000** | -1.000 | 0.0% |
| `IP_Q49` | `IP` | Does the Company present thorough and thoughtful financials? | 4 | **1.000** | -1.000 | 0.0% |
| `ES_Q2` | `ES` | Clearly maps applicable SDGs across the company’s value chain (Tw... | 5 | **0.900** | -0.900 | 0.0% |
| `PMF_Q32` | `PMF` | Has the startup identified customer experience pain-points in at ... | 5 | **0.800** | -0.800 | 20.0% |
| `M_Q9` | `M` | Has the startup created a customer feedback channel within the sa... | 5 | **0.800** | -0.800 | 20.0% |
| `L_Q23` | `L` | Has the company evaluated their patent portfolios? | 5 | **0.800** | +0.800 | 20.0% |
| `L_Q24` | `L` | Has the company evaluated their products? | 5 | **0.800** | -0.800 | 20.0% |
| `L_Q26` | `L` | Does the company know whether customers buy its products based on... | 5 | **0.800** | -0.800 | 20.0% |
| `L_Q31` | `L` | Has the company identified business information that is known to ... | 5 | **0.800** | +0.800 | 20.0% |
| `L_Q42` | `L` | Does the Company own, or plan to acquire, real or material person... | 5 | **0.800** | -0.800 | 20.0% |

## 5. Architectural Implications for Layer 2
1. **Business Canvas (`BC`) & Market (`M`):** Exhibit lowest exact matches (<60%) and highest withholdings, directly reflecting missing customer discovery / market matrix primary document routing.
2. **Over-prediction on Quantitative Criteria (`F_Q11`, `F_Q14`, `PMF_Q30`):** Confirms why Task 1 line-bounded deterministic evaluator is strictly needed.
3. **Visual Deck Criteria (`IP_Q7`, `PMF_Q24`):** Confirm 100% failure rate on diagram/flowchart criteria, proving the hypothesis in Task 4.
