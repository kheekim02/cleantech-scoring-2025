# CleanTech Open 2025 Diligence Engine — Comprehensive Knowledge Base

This document serves as the exhaustive architectural and operational reference for the CleanTech Open 2025 Diligence Engine platform.

---

## 0. Project Boundaries & Prototype Distinction (Strict Rule)

- **This Repository (`site/`, `api/`)**: Internal Human Scoring Prototype for CleanTech Open 2025 (Global Key Advisors + CleanTech Open) using **Vercel + Supabase**. It is solely for internal cohort evaluation.
- **Nafees's Due Diligence Scoring Platform**: A separate due diligence prototype created by coworker **Nafees**. It is **not** this codebase.
- **FrontSignal MVP**: The upcoming AWS-backed production intelligence platform (AWS Cognito, IAM, S3, DGX Spark, Cloudflare).
- **Rule**: Never conflate these systems. Always ask for clarification before making architectural assumptions about any prototype.

---

## 1. System Architecture & Component Interactions

```
  ┌────────────────────────────────────────────────────────┐
  │                 Supabase PostgreSQL                   │
  │  - startup_extractions (JSONB payloads; AI is ops-only)│
  │  - human_reviews (scorer points, justifications)       │
  │  - judge_assignments (evaluator cohort mappings)       │
  └───────────────────▲──────────────────┬─────────────────┘
                      │                  │
        REST / Edge Functions      REST / Edge Functions
                      │                  │
  ┌───────────────────┴──────────┐   ┌───┴────────────────────────┐
  │      Scorer Workspace        │   │       Admin Portal         │
  │      (site/index.html)       │   │     (site/admin.html)      │
  │  - Embedded PDF Deliverables │   │  - Evaluator Assignments   │
  │  - 282 Diligence Criteria    │   │  - Cohort Progress Stats   │
  │  - Human score saving only   │   │  - Human CSV export        │
  │  - No AI scores / citations  │   │  - Clean Ready Filter      │
  └──────────────────────────────┘   └────────────────────────────┘
```

### Product goals (UI boundary)
- **Human-only scorer UI**: judges see founder PDFs, rubric prompts, and their own scores/justifications.
- **No AI in the interface**: do not surface AI suggestions, confidence, citations, or citation auto-jump in `site/` judge/admin scoring surfaces.
- **AI stays offline / ops-side**: extraction caches and audits may exist for pipeline QA and research; they must not be part of the judge-facing API contract.
- **Optimize the human path**: slim payloads, reliable `human_reviews` sync, stable PDF viewing, assignments, and human-score exports.

---

## 2. Database Schema Reference

### `startup_extractions` Table
Master repository for parsed startup deliverables, AI predictions, and document metadata.
- `startup_id` (TEXT, PK): Unique company folder identifier (e.g. `2DaLoop`, `Novagrid`).
- `company_name` (TEXT): Display name of the startup.
- `payload` (JSONB): Structured document object:
  - `human_questions` (Array): Array of 282 criteria matching `master_282_rubric.json`:
    - `q_id` / `new_q_id`: Criterion identifier (e.g. `BC_Q1`, `IP_Q58`).
    - `cat_code`: Category code (`BC`, `ES`, `F`, `IP`, `IS`, `L`, `M`, `PMF`, `T`, `TP`).
    - `text`: Prompt question text.
    - `ai_suggestion`: Extracted numerical prediction (`0.0`, `0.25`, `0.5`, `0.75`, `1.0`, or `null`).
    - `ai_confidence`: Confidence float (`0.0`–`1.0`).
    - `verbatim_citation`: Extracted textual evidence from founder deliverable.
    - `source_pdf`: Associated PDF filename.
    - `page_number`: 1-based page number where citation appears in `source_pdf`.
  - `meta`: Operational flags (`clean_ready`: true, `clean_updated_at`: ISO timestamp).

### `human_reviews` Table
Stores judge submissions and draft evaluation entries.
- `id` (BIGINT, PK): Unique review entry ID.
- `startup_id` (TEXT): Foreign key referencing `startup_extractions.startup_id`.
- `question_id` (TEXT): Rubric criterion code (e.g. `BC_Q1`).
- `score_value` (NUMERIC): Evaluator awarded score (`0.0`, `0.25`, `0.5`, `0.75`, `1.0`).
- `justification` (TEXT): Reviewer explanation and notes.
- `reviewer_id` (TEXT): Evaluator identifier / email.
- `updated_at` (TIMESTAMPTZ): Last updated timestamp.

### `judge_assignments` Table
Tracks cohort reviewer distribution.
- `id` (BIGINT, PK)
- `judge_id` / `judge_name` (TEXT)
- `startup_id` (TEXT)
- `status` (TEXT: `pending`, `in_progress`, `completed`)

---

## 3. The 282 Diligence Criteria Breakdown

The master scoring catalog contains 282 questions across 10 evaluation categories:

| Category | Code | Q Count | Deliverable Focus |
| :--- | :---: | :---: | :--- |
| **Business Canvas** | `BC` | 5 | Value proposition, customer segmentation, customer discovery (>=5 interviews), BMC completeness. |
| **Environmental & Social** | `ES` | 10 | UN SDGs mapping, climate mitigation/adaptation priority, quantifiable sector superiority, environmental certifications. |
| **Financials** | `F` | 29 | 3-year revenue and expense model, COGS, unit economics, gross margins, capital requirements, break-even timelines. |
| **Investor Pitch** | `IP` | 58 | Diligence deck evaluation, problem clarity, competitive moat, business model feasibility, go-to-market execution, return profile. |
| **Executive Summary** | `IS` | 34 | Core executive summary narrative, quantified GHG impact, emission reduction calculations, strategic milestones. |
| **Legal & Governance** | `L` | 53 | Entity formation (e.g. Delaware C-Corp), patent grants/applications, IP assignments, cap table equity distribution, advisory board qualifications. |
| **Market & Customers** | `M` | 12 | Customer segmentation matrix, competitive landscape positioning, target customer profile, addressable market validation. |
| **Product Market Fit** | `PMF` | 34 | Discovery interview logs (4+, 6+, 10+ interviews), customer feedback mechanisms, willingness-to-pay ranges, buyer decision makers. |
| **Team Targets** | `T` | 31 | Founder experience, team target hiring plans, execution milestones, governance and operational readiness. |
| **Tech / Product** | `TP` | 16 | Product readiness, lab validation data, third-party performance testimonials, technical moat and feasibility. |

---

## 4. Scaffolding Stripping & Extraction Pipeline

### Why Scaffolding Stripping is Mandatory
Accelerator deliverables are completed on top of standardized competition templates containing lengthy instructional prompts, loose examples, and scoring criteria. Uncleaned language models mistakenly extract the template's own instructions as founder evidence.

### Pipeline Execution
1. **Catalog Construction (`scripts/extract_scaffolding_catalog.py`)**:
   Analyzed 1,481 files across 92 startups. Identified all recurring phrases exceeding a **20% frequency threshold** within each deliverable type.
2. **Text Cleaning (`clean_parsed_documents.py`)**:
   Stripped all cataloged scaffolding blocks from parsed document text.
3. **Extraction Daemon (`08_ai_copilot_extractor_clean.py`)**:
   Batched 282 criteria prompts against clean startup text using remote GPU acceleration on Spark server (`136.24.130.250`).
4. **Reverse-Indexing (`13_push_clean_extractions_to_supabase.py`)**:
   Indexed 17,278 extracted citations against raw PDF page text using exact, 8-word prefix, 5-word prefix, and quoted substring matching.
   - Result: **16,006 citations (92.6%)** matched to exact PDF file and page numbers.
   - All 92 active startups flagged with `clean_ready = true`.

---

## 5. Frontend Navigation (Human-Only Scoring)

### Side-by-Side Split Workspace
The scorer interface ([`site/index.html`](../site/index.html)) provides zero-tab-switching **human** evaluation. AI suggestions and citations are intentionally **not** shown:
- **Left Panel (PDF Viewer)**: Embedded `<iframe id="pdf-frame">` with browser controls, page selection, and a deliverable selector dropdown.
- **Right Panel (Criteria Cards)**:
  - Header: Category badge and criterion ID (no AI suggestion pill).
  - Text: Diligence prompt question.
  - Justification: Input field with optional `📄 View Examples` modal for calibrated criteria.
  - Point Selector: `1 PT`, `0.75 PTS`, `0.5 PTS`, `0.25 PTS`, `0 PTS`.
  - Flags / progress: human review state only.

### Explicit non-goals for the interface
- Do **not** re-enable AI suggestion badges, confidence display, citation dossiers, or auto-jump from model evidence.
- Offline extraction/push scripts may still store AI fields in `startup_extractions.payload` for ops; the scorer API should omit them from judge-facing responses.

---

## 6. Citation / rationale remediation (2026-10-03)

**Problem:** Independent uniqueness audit on `ai_cache_v5_parsed` was RED (1,818 HARD) while production `audit_v5_parsed` stayed GREEN. Dominant cause was accept-path writers (`_sanitize_rationale` constant string, timeout/missing-primary prose) manufacturing cross-company clones — not citation fabrication.

**Remediation (targeted, not blind full rescore):**
1. Schema + auditor: `error_code` on `QuestionEvaluation`; HARD G3.2 only for non-zero/engineered clones; true-negative similarity is SOFT.
2. Accept path: structured withholds (`TIMEOUT` / `NO_PRIMARY` / `WITHHELD_*`) with `rationale=null`; G2.3 mismatch reject; company-token prompt; retry-only `temperature=0.2`.
3. Offline scrub → selective regen → corpus scaffolding stub expansion → sample5 HARD=0 gate → full `needs_regen` + follow-up pass.
4. **Promoted:** `ai_cache_v5_parsed` (backup `ai_cache_v5_parsed_pre_remediation_20261003T214821Z`). Symlink `ai_cache_v5_remediated` → promoted path.

**Gate results after promote:**
| Gate | Before | After |
|---|---|---|
| Independent HARD | 1,818 RED | **0 GREEN** |
| `audit_v5_parsed` | 92/92 PASS | **92/92 PASS** |
| Engineered rationale strings | 1,885 | **0** |
| Scored coverage | 22,437 | 22,105 (−332 sanitize/timeout→withhold drift) |

**Closeout:** `/data/scraping/outputs/citation_remediation_closeout.json` (also under `datasets/cto_accelerator/`). **Supabase push not run** — awaiting explicit go-ahead; UI remains human-only.

**Wave 0 (2026-10-03):** Post-promote `*.primary_map.json` self-loop symlinks restored — 92/92 real files copied from `ai_cache_v5_parsed_pre_remediation_20261003T214821Z`. Integrity gate: `scripts/check_cache_integrity.py`. Independent re-audit on promoted path: HARD=0, no G0.0. Closeout: `citation_wave0_closeout.json`.

**Wave 1 (2026-10-04):** Offline hygiene — 1,330 shadow withholds → `NO_EVIDENCE`; scaffolding/junk micro-cite cleanup; G1.4 entity-only short-cite exemption; G3.1 indexes scaffolding cites even at 0.0. Independent HARD=0, SOFT≈11.0k. Closeout: `citation_wave1_closeout.json`.

**Wave 2 (2026-10-04):** `ES_Q1` accept/prompt redesign (narrative impact OK; invented `SDG N`/`$`/`%` still blocked) + selective regen (92 rows, `qwen3.8:27b-32k`). `ES_Q1` withheld 90→14 (15.2%); scaffolding nonzero 0; independent HARD=0. Closeout: `citation_wave2_closeout.json`.

**Wave 3 (2026-10-04):** Promote hardening — `scripts/promote_cache_gate.py` (integrity → independent HARD=0 → v5 grounding → atomic `--apply` only if GREEN; refuses symlink primary_maps; **refuses Supabase**). Scrub asserts copied maps are never symlinks. Check-only on live cache GREEN. Closeout: `citation_wave3_closeout.json`.

**Roadmap before → after (Waves 0–3):**

| Metric | Pre-critique / broken | After Waves 0–3 |
|---|---|---|
| Primary maps readable | 0/92 (self-loop symlinks) | **92/92 real files** |
| Independent HARD | 1,818 → broken G0.0 post-promote | **0 GREEN** |
| Shadow withholds (`null`/`null`) | 1,330 | **0** (`NO_EVIDENCE`) |
| `ES_Q1` withheld | 90/92 (97.8%) | **14/92 (15.2%)** |
| Template non-zero cites (`IS_Q21`-class) | ≥1 | **0** |
| Engineered rationale strings | 1,885 → 0 | **0** |
| Supabase / UI AI citations | N/A | **Not pushed / not enabled** (human-only interface) |

**Promote procedure (ops):**  
`python scripts/promote_cache_gate.py --candidate <remediated> --live .../ai_cache_v5_parsed --check-only`  
then `--apply` only when GREEN. Never run `15_push_v2_extractions_to_supabase.py` for this remediation — judge UI stays human-only.

---

## 7. Data Provenance & Authoritative Datasets Layout (Spark Remote)

All authoritative model evaluation, extraction caches, and cohort deliverable datasets reside on the Spark remote server (`136.24.130.250`) under `/data/scraping/datasets/cto_accelerator/`.

### Directory Layout & Canonical SoR Pointer
```text
/data/scraping/datasets/cto_accelerator/
├── ai_cache_promoted -> ai_cache_v5_parsed  # Canonical pointer to currently promoted SoR
├── ai_cache_v5_parsed/                      # Audited extraction cache (92 active startups, 282 criteria)
├── ai_cache_v5_remediated -> ai_cache_v5_parsed
├── parsed_clean_v4/                         # Authoritative Docling cleaned markdown corpus
├── raw/                                     # Raw deliverable PDFs (96 company directories)
├── active_startup_allowlist.json            # 92 active cohort startup IDs
├── master_282_rubric.json                   # Frozen 282-criteria rubric definitions
├── scaffolding_master_catalog.json          # Master 15-deliverable scaffolding catalog
├── pipeline_baseline.json                   # Pipeline performance baseline
└── archive/                                 # Historical datasets & pre-remediation snapshots
    ├── ai_cache_v5_parsed_pre_remediation_20261003T214821Z/
    ├── ai_cache_v3_strict/
    ├── ai_cache_v4_shadow/
    ├── ai_cache_v5_sample5/
    ├── legacy_2025/
    ├── parsed/
    └── parsed_clean/
```

### Data Provenance & Verification Invariants (Mandatory)
1. **Canonical SoR Resolution:**
   - Production consumption and offline calibration scripts must read from `ai_cache_promoted` (or an explicitly provided `--cache-dir`). Silent relative fallbacks to stale local folders are strictly prohibited.
2. **Structural Validation Over Version String Hardcoding:**
   - Never write brittle code asserting hardcoded version strings like `cache_type == "v5_parsed"`.
   - Instead, scripts validate **structural contracts**:
     - Exactly 92 allowlisted startup JSON files present.
     - Exactly 282 criteria records per startup matching `master_282_rubric.json`.
     - Validated schema compliance via `src/scorer/schemas.py` (`error_code`, `citation`, and `predicted_val`).
3. **Mandatory Provenance Header in Quantitative Reports:**
   - Every quantitative report, distribution audit, or IRR analysis must log its dataset provenance (source host, path, symlink target, startup count, record count, and timestamp) in its output header.

