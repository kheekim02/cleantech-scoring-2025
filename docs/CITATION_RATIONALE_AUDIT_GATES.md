# Independent Citation & Rationale Audit Gates

**Scope:** `ai_cache_v5_parsed` cohort (92 companies × 282 questions)  
**Purpose:** Define the *optimal* citation/rationale shape *before* scoring generated output.  
**Independent of:** `audit_v5_parsed.py` (that is the production gate; this is a second opinion).

---

## G0 — Record integrity (hard)

| ID | Gate | Pass condition |
|---|---|---|
| G0.1 | Allowed score | `predicted_val ∈` rubric options (else `{0,0.25,0.5,0.75,1.0}`) |
| G0.2 | Confidence | `0.0 ≤ confidence ≤ 1.0` |
| G0.3 | Rationale present | Non-empty `rationale` whenever `predicted_val` is set |
| G0.4 | Non-zero needs cite | If `predicted_val ≠ 0.0`, `citation` is a non-empty string |

---

## G1 — Optimal citation shape

An **optimal citation** is a judge-usable verbatim pull-quote from *this* company's founder deliverable.

| ID | Gate | Optimal / Pass | Fail |
|---|---|---|---|
| G1.1 | Verbatim ground | Exact continuous span of category primary markdown (`match_citation_to_text`) | Ungrounded / paraphrased / stitched |
| G1.2 | Not scaffolding | Not Cleantech Open / module assignment / template language | Scaffolding patterns |
| G1.3 | Not meta-commentary | Not evaluator prose (“the document does not…”, “no evidence…”) when score > 0 | Negative/meta citation on positive score |
| G1.4 | Sentence-ish length | Prefer **8–80 words** (1–2 complete sentences). Soft warn if outside; hard fail if `< 3` words on non-zero score **except** grounded **entity-like** proper-name cites of 1–3 tokens (SOFT). Junk micro-stubs (`NA`, `No`, markdown-only, canvas headers) are HARD even if grounded. | Empty / junk / ungrounded micro-stub / essay dump (>120 words = warn) |
| G1.5 | Company-local | Citation tokens overlap this company's primary text (implied by G1.1). Cross-company identical cite → G3 |

**Zero-score exception:** `citation` may be `null`. If present, it must still pass G1.1–G1.2 (real founder words showing a deficit), never fabricated absence-commentary that fails grounding.

---

## G2 — Optimal rationale shape

An **optimal rationale** is a 2–4 sentence audit note that *shows its work* on this packet.

| ID | Gate | Optimal / Pass | Fail |
|---|---|---|---|
| G2.1 | Length | **20–120 words** preferred; hard fail if `< 8` words | Empty / one-liner fluff / wall of text (>200 words = warn) |
| G2.2 | Descriptive deficit | Names concrete founder content (segment, metric, competitor, product) before pass/fail — not only “lacks evidence” | Pure generic deficit language with no company-specific token |
| G2.3 | Score alignment | If rationale asserts absence / “does not state/mention/provide”, score must be `0.0` (or ≤ `0.25` if soft hedging) | Absence language + score ≥ `0.5` |
| G2.4 | Claim grounding | `$…`, `%`, `SDG N` in rationale appear in primary text or citation | Invented figures |
| G2.4a | ES_Q1 / SDG questions (accept-path) | Non-zero scores require grounded citation with either an SDG label in primary **or** impact-narrative tokens in the citation; invented `SDG N` still HARD via G2.4 | Blind score with neither label nor narrative |
| G2.5 | No boilerplate bank | Rationale is not in the blocked generic phrase list (below) | Hits blocked phrase as the *substance* of the rationale |

### Blocked generic rationale phrases (G2.5)

Normalized match (substring after lowercasing / whitespace collapse):

- `lacks concrete evidence`
- `insufficient information`
- `insufficient evidence`
- `the document provides a clear`
- `the document clearly articulates`
- `based on the provided information`
- `as stated in the document`
- `meets the criteria`
- `does not meet the criteria` *(alone, with no named founder detail)*
- `no relevant information was found`
- `unable to determine`
- `the startup demonstrates a strong`

---

## G3 — Cross-company uniqueness (hard / soft)

Generated answers must not be copy-pasted or near-templated across startups for the same `q_id` when those answers carry a **non-zero score**. True-negative blanks may share similar absence language without failing the cohort.

| ID | Gate | Pass | Fail |
|---|---|---|---|
| G3.1 | Exact citation clone | Same normalized citation for same `q_id` in **≥ 2** companies when score is **non-zero** **or** the citation is scaffolding/template text (even at 0.0) | HARD cluster |
| G3.2 | Exact rationale clone | Same normalized rationale for same `q_id` in **≥ 2** companies when score is non-zero, **or** any engineered pipeline string | HARD cluster |
| G3.2 Soft | True-negative absence clones | Identical/near-identical absence rationales when `predicted_val is null` or (`predicted_val == 0.0` and `citation is null`) | SOFT only (does not block GREEN) |
| G3.3 | Near-duplicate rationale | Token Jaccard ≥ **0.92** for same `q_id` across companies (length ≥ 12 tokens) | SOFT clusters |
| G3.4 | Cross-q generic cite bank | Same normalized citation reused across **≥ 3** distinct `q_id`s *within one company* is OK; across **≥ 5 companies** for unrelated q_ids is flagged as a global cite template | SOFT global template |

**Exempt from HARD G3:** empty / null citations on zero scores; citations shorter than 12 chars after normalize; true-negative absence rationales (null/0.0 + null citation) that are not engineered pipeline strings.

**Always HARD:** engineered pipeline rationales (`Score based on the cited primary text only.`, `Evaluation failed or timed out`, `No primary source…`, `Score withheld:…`) regardless of score.

---

## Cohort pass / fail policy

| Level | Rule |
|---|---|
| **HARD fail** | Any G0.*, G1.1–G1.3, G1.4 micro-stub on non-zero, G2.3–G2.4, engineered G2.5, HARD G3.1–G3.2 |
| **SOFT fail (warn)** | G1.4 bounds, G2.1 bounds, G2.2, non-engineered G2.5, soft G3.2 true-negatives, G3.3–G3.4 |
| **Cohort GREEN** | Zero HARD findings; SOFT findings reported but do not block |
| **Cohort RED** | ≥1 HARD finding |

Report artifact: JSON summary with per-gate counts, top clone clusters, and sampled failures.

---

## Promote gate (Wave 3)

Before renaming any candidate cache over `ai_cache_v5_parsed`, run:

`scripts/promote_cache_gate.py --candidate <dir> --live .../ai_cache_v5_parsed --check-only`

Required GREEN: integrity (no symlink primary_maps) → independent HARD=0 → cohort v5 grounding PASS.  
`--apply` performs atomic backup+rename only when GREEN. **Supabase push is refused** (judge UI is human-only).
