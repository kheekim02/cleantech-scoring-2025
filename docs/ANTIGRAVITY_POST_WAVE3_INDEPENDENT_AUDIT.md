# Antigravity independent audit — post Waves 0–3

**Copy the fenced `text` block below into Antigravity.**  
Do not treat this file as the audit result; it is the review brief.

---

```text
You are a senior diligence QA reviewer for the CleanTech Open 2025 scoring stack (startup_scorer). Independently re-audit the promoted AI citation/rationale cohort AFTER Waves 0–3 remediation. Be adversarial: verify whether the prior YELLOW findings are actually closed, and surface any new HARD-class or material soft failures. Do not modify production data. Do not push Supabase. Do not re-enable AI in the judge UI.

## Context (do not assume chat memory)
- Project root (local): `/Users/geoffrey/.gemini/antigravity/scratch/startup_scorer`
- Spark host: `jkim@136.24.130.250`
- Promoted cache (SoR): `/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed`
  - Each company: `{startup_id}.json` (282 records) + `{startup_id}.primary_map.json` (must be REAL files, not symlinks)
- Pre-remediation backup: `/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed_pre_remediation_20261003T214821Z`
- Primary markdown: `/data/scraping/datasets/cto_accelerator/parsed_clean_v4/{startup_id}/`
- Gates: `docs/CITATION_RATIONALE_AUDIT_GATES.md` (also on Spark under `datasets/cto_accelerator/`)
- Roadmap: `docs/CITATION_POST_PROMOTE_REMEDIATION_ROADMAP.md`
- KB: `docs/KNOWLEDGE_BASE.md` § citation remediation + Waves 0–3
- Closeouts (Spark + local `outputs/`):
  - `citation_remediation_closeout.json` (original promote)
  - `citation_wave0_closeout.json` … `citation_wave3_closeout.json`
- Promote gate report: `/data/scraping/datasets/cto_accelerator/promote_gate_report_wave3.json`
- Latest independent audit JSON: `/data/scraping/datasets/cto_accelerator/citation_independent_audit.json`
- Scripts on Spark: `/data/scraping/scripts/` (`audit_citations_independent.py`, `check_cache_integrity.py`, `promote_cache_gate.py`, `audit_v5_parsed.py`, `14_ai_copilot_extractor_v2.py`)
- Schema: `/data/scraping/src/scorer/schemas.py` (also local `src/scorer/schemas.py`)
- Python on Spark: `/data/scraping/venv/bin/python` with `PYTHONPATH=/data/scraping` (or `cd /data/scraping`)

## Claimed post-Wave-3 state (challenge these; do not rubber-stamp)
| Metric | Claimed now |
|---|---|
| Primary maps readable | 92/92 real files; 0 symlinks |
| Independent HARD | 0 GREEN |
| Soft findings | ~11,055 (G1.4≈3153, G2.1≈5140, G3.2 soft≈417, G3.3≈2327) |
| Engineered rationale strings | 0 |
| Shadow withholds (`null` score + `null` error_code) | 0 |
| Scaffolding cites on non-zero scores | 0 |
| `ES_Q1` withheld | 14/92 (15.2%); scored 78 (77×1.0, 1×0.0) |
| Promote gate check-only | GREEN; Supabase refused |
| Judge UI AI citations | Still disabled / not pushed |

Prior Antigravity YELLOW (must explicitly re-check):
1. Circular `*.primary_map.json` self-loop symlinks (G0.0)
2. `Vaanelai` `IS_Q21` score 1.0 on Markets template scaffolding
3. `PMF_Q5` sampling worksheet cites / scaffolding gaps
4. G1.4 junk micro-cites (`NA`, `No`, `## Diagram`) on non-zero
5. 1,330 shadow withholds (`null`/`null`)
6. `ES_Q1` wipe (90/92 withheld)

Policy that is NOT a HARD reopen unless you find new evidence:
- Soft true-negative absence rationale similarity (G3.2 Soft / G3.3)
- Telegraphic G2.1 short rationales without a selective regen mandate
- Supabase / UI AI enablement (explicit non-goal)

## Review objectives
1. **Operability:** every primary_map is a readable real file; `check_cache_integrity.py` GREEN; independent auditor runs without G0.0.
2. **Prior YELLOW closure:** each of the six items above is closed, narrowed, or still open — with evidence.
3. **Faithfulness:** non-zero citations are exact continuous spans of that company's category primary; not scaffolding; not meta-absence on non-zero.
4. **Rationale quality / claims:** no invented `$` / `%` / `SDG N` absent from citation/primary; score↔rationale aligned (no absence language with score ≥ 0.5).
5. **ES_Q1 redesign sanity:** narrative-impact scores must still be grounded; inventing SDG numbers must still fail; quantify remaining 14 withholds — correct vs over-aggressive.
6. **Promote hardening:** confirm `promote_cache_gate.py` refuses symlink maps and refuses Supabase; scrub path copies maps (no symlink write).
7. **Usefulness residual:** even if HARD=0, name the top soft patterns that still hurt ops QA (with counts).

## Method (required)
Work on Spark for cohort-scale reads.

A. SSH check; read wave0–wave3 closeouts + roadmap + promote_gate_report_wave3.json + latest independent audit JSON.
B. Run (or re-run and compare):
   - `/data/scraping/venv/bin/python /data/scraping/scripts/check_cache_integrity.py --cache-dir .../ai_cache_v5_parsed --out /tmp/integrity_antigravity.json`
   - `/data/scraping/venv/bin/python /data/scraping/scripts/audit_citations_independent.py --cache-dir .../ai_cache_v5_parsed --rubric .../master_282_rubric.json --out /tmp/audit_antigravity.json`
   - Optional: `/data/scraping/venv/bin/python /data/scraping/scripts/promote_cache_gate.py --candidate .../ai_cache_v5_parsed --check-only --out /tmp/promote_gate_antigravity.json`
C. Prove maps: count symlinks among `*.primary_map.json` (expect 0); sample-read 3 maps.
D. Prove engineered/shadow/scaffolding-nonzero cleared with cohort scans (use `is_engineered_rationale`, `is_scaffolding_citation` from schemas).
E. Stratified manual sample (minimum 10 companies):
   - Fixed: CarbonDots, Cero_Global_Holdings, Hubbletek, SOLARSYSTEMS, SPCTA_Industrial, Vaanelai, H2O_Now, Apex_Engineering_AI
   - Plus 2 random others (seed=43)
   - Per company ≥8 records spanning: non-zero cited, zero/true-negative, withheld (`error_code`), short cite/rationale if present
   - For every sampled non-zero: verify citation with `match_citation_to_text` against **live** `{company}.primary_map.json` (not only backup)
F. Special checks:
   - `Vaanelai` `IS_Q17` / `IS_Q21` / `ES_Q1` current rows
   - `ES_Q1` cohort score/error_code histogram; sample 5 of the remaining withholds and 5 of the score=1.0 narrative rows for invented-SDG risk
   - Search residual engineered strings: "score based on the cited primary text only", "evaluation failed or timed out", "no primary source document", "score withheld:"
   - Spot-check whether `NA`/`No`/`## Diagram` still appear as non-zero cites
G. Soft clusters: inspect top soft G3.2 / G3.3 from audit JSON — classify acceptable true-negative vs silent mode-collapse that should be HARD.
H. Do NOT modify cache, do NOT `--apply` promote, do NOT call any Supabase push script.

## Deliverable format (raw markdown, no filler)
## VERDICT:
[GREEN / YELLOW / RED] — one sentence on whether Waves 0–3 made citations/rationales operable + judge-usable as ops QA SoR.

## PRIOR_YELLOW_DISPOSITION:
Table: prior finding → CLOSED / PARTIAL / OPEN → evidence (path/count/quote).

## HARD_RESIDUALS:
Any remaining HARD-class issues with company, q_id, gate, evidence. Empty only if none.

## SOFT_BUT_MATERIAL:
Top residual soft patterns with counts; say whether they should stay SOFT by policy.

## SAMPLE_FINDINGS:
Bullets from stratified sample (≥3 failures/near-failures if any exist; else strongest passes + borderline).

## ES_Q1_AND_COVERAGE:
ES_Q1 histogram; remaining withhold assessment; any category wipeouts still extreme.

## PROMOTE_AND_PROCESS:
Integrity / promote-gate / scrub symlink posture; Supabase status.

## AUTOMATION_GAPS:
What auditors still miss that this review caught.

## REQUIRED_ACTIONS:
Concrete next steps for another agent. If roadmap is complete for ops SoR, say so and list only optional debt. Never recommend Supabase/UI AI enablement unless evidence shows it is required (it is not).

## CONFIDENCE:
[Certain / Likely / Guessing] on the verdict + one-line justification.

Constraints:
- Lead with uncomfortable truths.
- Prefer Spark evidence over vibes.
- If SSH fails, stop and say so; do not invent sample findings.
```
