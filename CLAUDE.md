# CleanTech Open 2025 Diligence Engine — AI Workspace Rules & Knowledge Base

This file defines the architecture, engineering protocols, prompting standards, data integrity safeguards, and operational knowledge for all AI models working within this repository.

---

## 1. Core System Overview

The **CleanTech Open 2025 Diligence Engine** is an end-to-end diligence, scoring, and triage platform for clean technology startups. Expert human judges and administrators evaluate founder submissions across 10 standardized categories using founder PDF deliverables and a human-only scoring workspace. Offline AI extraction may still run for ops/analysis but **is not shown in the judge interface**.

### Key Architecture Components
- **Frontend Scoring Portal (`site/index.html`)**: Side-by-side split workspace featuring an embedded PDF viewer (left) with dynamic document switching, paired with interactive 282-criteria human scoring cards (right). **No AI scores, suggestions, or citations are shown in the judge UI.**
- **Admin Dashboard (`site/admin.html`)**: Cohort-level progress tracking, reviewer/judge assignment workflow, filter for clean AI-ready startups (`✓ Ready for Assignment`), and human-score audit CSV exports.
- **Client Architecture (`site/js/`)**: Vanilla JS modular application:
  - `app.js`: State management, event delegation, Supabase API communication, rubric modal handlers.
  - `render.js`: High-velocity DOM rendering for human scoring cards, PDF embedder, and document switchers (AI assist UI is intentionally absent).
  - `scoring.js`: Dynamic progress calculation, score aggregation, and completion tracking.
  - `admin.js`: Administrative metrics, bulk judge assignments, and cohort progress filters.
  - `export.js`: Diligence audit logs and submission exports (human scores).
- **Database & Persistence**: Supabase PostgreSQL with queued persistence for scores/justifications:
  - `startup_extractions`: Master table storing startup payloads (JSONB) and readiness metadata. AI extraction fields may exist for ops but are not part of the judge-facing UI contract.
  - `human_reviews`: Stores judge scores (`numeric` allowing `0.0`, `0.25`, `0.5`, `0.75`, `1.0`), textual justifications, and reviewer IDs.
  - `judge_assignments`: Manages evaluator-to-startup allocations and completion statuses.
- **Serverless API Layer (`api/`)**: Netlify / Supabase edge functions:
  - `get-startup.js`: Fetches startup payload and hydrates existing judge reviews.
  - `save-score.js`: Debounced real-time persistence for scores and justifications.
  - `list-startups.js`: Supplies startup lists and metadata to dashboards.

---

## 2. Master Rubric Standard (282 Criteria)

All diligence evaluation is standardized against **`master_282_rubric.json`**, consisting of exactly **282 questions** across 10 evaluation categories:

| Code | Evaluation Category | Question Count | Question ID Range | Source Deliverable |
| :--- | :--- | :---: | :--- | :--- |
| **BC** | Business Canvas | 5 | `BC_Q1` – `BC_Q5` | Business Model Canvas (EBD1) |
| **ES** | Environmental & Social | 10 | `ES_Q1` – `ES_Q10` | Impact Statement (EBD2) & Sustainability Questions |
| **F** | Financials | 29 | `F_Q1` – `F_Q29` | 3-Year Financial Projections (EBD5) & Unit Economics |
| **IP** | Investor Pitch | 58 | `IP_Q1` – `IP_Q58` | Investor Pitch Deck (EBD8) |
| **IS** | Executive Summary / Impact | 34 | `IS_Q1` – `IS_Q34` | 1-Page Executive Summary (EBD6) & Impact Strategy |
| **L** | Legal & Governance | 53 | `L_Q1` – `L_Q53` | IP Filings, Corporate Formation, Governance |
| **M** | Market & Customers | 12 | `M_Q1` – `M_Q12` | Customer Segments & Competitive Matrix (EBD3) |
| **PMF** | Product Market Fit | 34 | `PMF_Q1` – `PMF_Q34` | Customer Discovery Interviews Log |
| **T** | Team Targets | 31 | `T_Q1` – `T_Q31` | Hiring Plans, Targets & Milestone Tracking |
| **TP** | Tech / Product | 16 | `TP_Q1` – `TP_Q16` | Technology Validation (EBD4) |
| **TOTAL** | **10 Categories** | **282** | | **Standardized CleanTech Open Rubric** |

### Scoring Scale Calibration
- **Point Scale**: Standardized **0 to 1 point scale**:
  - `1 PT` (1.0)
  - `0.75 PTS` (0.75)
  - `0.5 PTS` (0.5)
  - `0.25 PTS` (0.25)
  - `0 PTS` (0.0)
- **Binary vs. Fractional**: Objective criteria default to binary (`0 PTS` / `1 PT`), while subjective/calibrated criteria support fractional tiers (`0.25`, `0.5`, `0.75`).
- **Business Canvas Rubric Examples**: The `📄 View Examples` modal for `BC_Q1` through `BC_Q5` provides real-world grading thresholds calibrated to this 0–1 point scale.

---

## 3. Scaffolding Elimination & Clean AI Extraction Pipeline

Founders in CleanTech Open submit standardized templates containing extensive instructions, prompt text, and placeholder examples (scaffolding). If left uncleaned, LLMs hallucinate positive matches by citing the competition's own template instructions.

### Deletion Catalog & Frequency Thresholds
- All documents are filtered against the **Master Scaffolding Catalog** (`data/MASTER_SCAFFOLDING_CATALOG.md` / `scaffolding_attribution_catalog.txt`).
- Threshold: Any text string appearing in **> 20% of cohort files** within a deliverable type is flagged as scaffolding and stripped prior to extraction.
- Covers 15 deliverable types (`EBD2`, `EBD3`, `EBD4`, `M1`–`M8`, `BMC`, `GHG`, `Inclusion`, etc.).

### Extraction Daemon & Remote Execution
- Extraction daemon: `scripts/08_ai_copilot_extractor_clean.py` executed on Spark remote server (`136.24.130.250`).
- Local cache mirror: `data/ai_cache_clean/` (93 files, 92 active startups).
- Expanded Citation Capture: Citations capture full multi-sentence context rather than truncated fragments.
- **Current Status**: **100% of 92 active startups** in Supabase are fully extracted and stamped with `payload.meta.clean_ready = true`.

---

## 4. Reverse-Indexing & Citation Page Mapping (Ops / Offline)

Extracted citations may still be grounded against founder text for pipeline QA and offline analysis. **This evidence is not surfaced in the scoring UI.**

### Multi-Tier Normalized Fuzzy Matcher (`scripts/13_push_clean_extractions_to_supabase.py`)
1. **Tier 1 (Exact Match)**: Normalized character sequence matching against full PDF text.
2. **Tier 2 (8-Word Prefix)**: First 8 normalized words matched against page text corpus.
3. **Tier 3 (5-Word Prefix)**: 5-word prefix match for specific terminology (>15 chars).
4. **Tier 4 (Quoted Substrings)**: Regex-extracted quote fragments (>10 chars).
- **Match Rate (historical)**: **16,006 of 17,278 citations (92.6%)** matched to exact PDF filename and page number.
- **UI policy**: Judges navigate PDFs manually via the deliverable selector and viewer controls. Do not reintroduce `🔗 View AI Citation` or AI suggestion badges into `site/`.

---

## 5. Engineering Protocols & Grounding Standards

1. **Zero Hallucination Tolerance (pipeline):**
   - Never invent financial numbers, valuation multiples, patent counts, or founder pedigree.
   - If an artifact lacks evidence for a question, output `"STATUS: INSUFFICIENT_DATA"` or award `0 PTS`.
2. **Human-Only Scoring Interface:**
   - The judge portal must not display AI suggestions, confidence, citations, or auto-jump from model evidence.
   - Judges score solely from founder deliverables and the rubric; they have full authority over all scores.
   - Prefer omitting AI fields from judge-facing API responses rather than merely hiding them in CSS/JS.
3. **Deterministic Output & Schema Conformance:**
   - All machine-readable pipeline outputs must be strict, valid JSON conforming to the 282-question schema.
4. **Git Hygiene & Commit Discipline:**
   - Atomic commits following Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
   - Pre-commit verification: verify scripts, tests, and builds cleanly before committing.

---

## 6. Operational Documentation & Sync

Tutorial manuals are generated via Chrome headless and kept synchronized on the user's Desktop:
- **Scorer Tutorial**: `/Users/geoffrey/Desktop/CleanTech_Open_Scorer_Tutorial.pdf` (5 pages)
- **Admin Tutorial**: `/Users/geoffrey/Desktop/CleanTech_Open_Admin_Tutorial.pdf` (6 pages)
- Generator script: `venv/bin/python3 scripts/generate_tutorials.py`
