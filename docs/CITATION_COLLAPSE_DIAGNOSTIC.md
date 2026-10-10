# Diagnostic: Why citations/rationales collapsed across the 92-company cohort

**Date:** 2026-10-03  
**Inputs:** Independent audit `citation_independent_audit.json` (RED: 1,818 HARD) + `scripts/14_ai_copilot_extractor_v2.py` + published citation-gate / judge literature  
**Scope:** Cause analysis and research-bounded expectations. **No remediation plan.**

---

## 1. What failed (symptoms → mechanisms)

| Audit symptom | Dominant mechanism | Evidence |
|---|---|---|
| **G3.2** identical rationales (999 clusters; e.g. ES_Q1 × 87 cos) | **Pipeline writes a fixed string**, not the model | `_sanitize_rationale()` always returns `"Score based on the cited primary text only."` (209 hits). Timeouts return `"Evaluation failed or timed out"` (254). Missing primary returns `"No primary source…"` (1,422). |
| Absence templates (“provided documents contain no…”) × 1,954 | **Greedy decoding + shared prompt + shared question** when evidence is truly absent | `temperature=0.0`; prompt asks for a **brief 1-sentence** rationale; same `q_id` across startups with empty evidence → same minimal English |
| **G2.3** absence language + score ≥ 0.5 (207) | Score/rationale inconsistency not blocked before accept | Production `audit_v5_parsed` does not enforce absence↔score alignment |
| **G3.1** citation clones (72; e.g. `less taxation 0 0 0` × 20) | **Shared assignment worksheets** still in primary markdown | Cleantech Open financial / interview templates appear verbatim in many packets; contiguous-span gate *correctly* accepts them |
| Tiny cites / short rationales (G1.4 / G2.1 HARD) | Prompt + `max_tokens` budget favor brevity | Schema: `"rationale": <brief 1-sentence explanation>` |

**Critical inversion:** The production gate (`audit_v5_parsed`) checks **within-company grounding**. That is why the cohort looked GREEN there while the independent uniqueness gate went RED. Grounding ≠ non-generic.

Ungrounded fabrication (G1.1) was **not** the main failure mode — citations largely *are* spans of primary text.

---

## 2. Root causes (ordered)

1. **Post-processor mode collapse (code bug / design)**  
   `_sanitize_rationale` replaces *any* inventing rationale with one constant sentence. That alone manufactures cross-company clones and destroys company-specific critique.

2. **Operational fallbacks that look like model output**  
   Timeouts and missing-category paths persist identical rationales into the cache; the audit treats them as “answers.”

3. **Prompt contract fights uniqueness**  
   “Brief 1-sentence” + “rationale may only repeat facts in the quote” + `temperature=0` optimizes for short, reusable English — especially on true negatives.

4. **No cross-instance diversity objective**  
   Nothing in accept/audit compares company A vs B for the same `q_id`. Literature shows self-*consistent* errors are *harder* to catch precisely because they repeat ([“Too Consistent to Detect,” EMNLP 2025](https://aclanthology.org/2025.emnlp-main.238.pdf)).

5. **Scaffolding / shared forms leak into “primary”**  
   Identical worksheet cells become “valid” citations under a pure verbatim rule — correct for grounding, wrong for diligence signal.

---

## 3. What GitHub / research actually solves (and does not)

### A. Verbatim citation gates (solve fabrication, not clone rationales)

| Project | Idea | Relevance here |
|---|---|---|
| [verbatim-citation-gate](https://github.com/Palo-Alto-AI-Research-Lab/verbatim-citation-gate) | Deterministic contiguous quote match *before* any LLM judge; reject frankenquotes / wrong-doc quotes | Aligns with what we already mostly pass (G1.1). Does **not** stop identical rationales. |
| [VeriQuote](https://github.com/rickintoplace/veriquote) / [citeguard](https://github.com/Franksterino/citeguard) | Quote must exist **and** entail the claim (NLI / LLM judge, fail-closed) | Would catch **G2.3/G2.4**-style score–claim mismatch. Still silent on cross-company templates. |
| QuoteVerify (quote-backed research reports) | Structured quote triples + substring + NLI; models still only 18–28% valid quotes in their setting | Confirms verbatim is the bottleneck *when* models paraphrase. Our bottleneck is the opposite: valid quotes + collapsed rationales. |

### B. Judge / rubric tooling (quality scoring, not anti-collapse)

| Project | Idea | Relevance |
|---|---|---|
| [grading-rubric-engine](https://github.com/prajst6/grading-rubric-engine) | Frozen weighted rubric + heuristic/LLM evaluators + flag borderline items | Pattern for **post-hoc** quality flags (like our independent audit), not generation diversity. |
| [prompt-variant-evaluation](https://github.com/agentpatternscatalog/patterns/blob/main/patterns/prompt-variant-evaluation.md) | Freeze rubric, A/B prompts offline, select by measurement | Process for choosing an upgraded prompt — does not by itself remove clones. |

### C. Consistency / diversity literature (explains the absence-template wall)

- **Temperature 0 / greedy decoding** collapses similar prompts to the same string; repeating the call does not surface error if the error is self-consistent (EMNLP 2025 above).
- **Batched self-consistency** ([arXiv:2505.12570](https://arxiv.org/abs/2505.12570)) improves ranking by *diversifying* subsets/order — opposite of our fixed one-shot `T=0` judge.
- Implication: uniqueness must be an **explicit accept criterion** (reject/retry or regenerate), not an assumed property of “being grounded.”

---

## 4. Bottom-line truth — what an upgraded pass can and cannot deliver

### Can accomplish (high confidence if designed for these)

| Outcome | Why research + code diagnosis say so |
|---|---|
| **Near-eliminate engineered clone strings** (`score based on…`, `evaluation failed…`, blanket sanitize) | These are not model behavior; removing/replacing the writer removes G3.2 mass clusters that are artifacts. |
| **Enforce claim⊨citation (or fail closed)** for figures / absence vs score | VeriQuote / citeguard / verbatim-citation-gate pattern; addresses G2.3/G2.4 class. |
| **Cut worksheet citation clones** among companies by stripping shared scaffolding before PRIMARY | Verbatim gate is working as designed; fix the *corpus*, not the matcher. |
| **Measurably lower cross-company rationale clones on true-negative questions** via: require ≥1 company-specific token (name/metric from quote); reject exact-normalized duplicates for `(q_id)` with retry; optional mild stochasticity **only** on rationale | Explicit diversity objective; literature says greedy judges won’t invent diversity alone. |

### Cannot / should not promise

| Non-goal | Why |
|---|---|
| **Zero similar “no evidence” rationales across 92 startups** | Many packets *truly* lack the same artifact (logo, branding hire, website archive). Semantically similar negatives are often *correct*. Forcing unique prose risks hallucinated specifics (QuoteVerify: models prefer paraphrase/invention under pressure). |
| **GREEN independent audit with current gates unchanged and no code/prompt change** | G3.2 is dominated by deterministic writers + T=0 absence English. |
| **Verbatim-only upgrades fixing uniqueness** | Research citation gates optimize faithfulness of quotes, not cross-instance rationale entropy. |
| **Self-consistency voting alone catching template collapse** | Self-consistent errors stay stable or worsen with scale; identical wrong/generic text looks “confident.” |

### Realistic upgraded-pass expectations (order-of-magnitude)

Assuming fixes target §2 causes (not a blind full re-score with the same accept path):

| Metric | Current | Plausible after targeted upgrade | Not realistic |
|---|---|---|---|
| Engineered rationale clones (sanitize/timeout/missing-primary as “answers”) | Hundreds–1.4k rows | **~0** persisted as fake rationales (null / withheld / distinct error channel) | — |
| Exact G3.2 clusters on open-ended questions | 999 | **Large drop** (order-of-magnitude) if reject+retry + no constant sanitize | 0 clusters forever |
| Absence-style similarity on true blanks | High | **Lower exact-match rate**; residual near-duplicates remain | Unique essay per company |
| G1.1 ungrounded cites | Already low | Stay low or improve slightly with frankenquote checks | Not the headline win |
| Independent audit HARD | 1,818 | Can reach **GREEN on uniqueness HARD** *if* gates treat true-negative similarity as SOFT and engineered clones as HARD | GREEN while keeping “any similar absence text = HARD” |

---

## 5. One-sentence truth

**The cohort did not mainly “hallucinate citations”; it passed verbatim grounding while the accept path and greedy 1-line rationales manufactured cross-company templates — research citation gates fix faithfulness, not uniqueness, so an upgraded pass can erase engineered clones and sharply reduce template collapse, but cannot honestly promise unique prose whenever many startups share the same missing evidence.**
