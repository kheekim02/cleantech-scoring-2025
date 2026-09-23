# CleanTech Open 2025 Diligence Engine

A high-velocity, AI-assisted diligence and scoring platform engineered for the **CleanTech Open 2025** accelerator cohort.

The platform provides a side-by-side workspace allowing expert judges and evaluators to review founder deliverables, inspect AI-extracted verbatim evidence, auto-jump directly to the cited PDF pages, and grade startups across a standardized 282-question diligence rubric with real-time database persistence.

---

## Key Features & Highlights

- **Side-by-Side Dual-Pane Workspace**: Split-screen interface with an embedded deliverable PDF viewer on the left (complete with page navigation, zoom, and document switching) and interactive scoring cards on the right.
- **Auto-Jumping Citation Navigation**: 16,006 AI-extracted citations reverse-indexed to source PDFs (92.6% match rate). Clicking a citation immediately shifts the document viewer to the exact deliverable and page.
- **Scaffolding-Stripped Grounded AI Extraction**: Filtered against a comprehensive cross-cohort catalog (>20% frequency across 1,481 files) to eliminate accelerator template instructions and prevent false-positive hallucinations.
- **Standardized 282-Criteria Diligence Rubric**: Full 10-category evaluation framework spanning Business Canvas, Environmental & Social, Financials, Pitch, Legal, Market, PMF, Team, and Tech Validation.
- **Calibrated 0 – 1 Point Scoring Scale**: Granular scoring (`0 PTS`, `0.25 PTS`, `0.5 PTS`, `0.75 PTS`, `1 PT`) with real-world examples and rubric guidance for Business Canvas questions (`BC_Q1`–`BC_Q5`).
- **Real-Time Database Persistence**: Keystroke-level saving to Supabase PostgreSQL (`human_reviews` table) with auto-hydration for returning evaluators.
- **Admin Management Portal**: Real-time evaluation progress tracking, judge assignment workflow, `✓ Ready for Assignment` filter, and CSV audit exports.

---

## Diligence Rubric (282 Criteria)

Evaluation is standardized across 10 categories in [`master_282_rubric.json`](./master_282_rubric.json):

| Code | Category | Questions | Question ID Range | Source Deliverable |
| :--- | :--- | :---: | :--- | :--- |
| **BC** | Business Canvas | 5 | `BC_Q1` – `BC_Q5` | Business Model Canvas (EBD1) |
| **ES** | Environmental & Social | 10 | `ES_Q1` – `ES_Q10` | Impact Statement (EBD2) & Sustainability Questions |
| **F** | Financials | 29 | `F_Q1` – `F_Q29` | 3-Year Financial Model (EBD5) & Unit Economics |
| **IP** | Investor Pitch | 58 | `IP_Q1` – `IP_Q58` | Investor Pitch Deck (EBD8) |
| **IS** | Executive Summary / Impact | 34 | `IS_Q1` – `IS_Q34` | 1-Page Executive Summary (EBD6) & Impact Strategy |
| **L** | Legal & Governance | 53 | `L_Q1` – `L_Q53` | IP Filings, Corporate Formation, Governance |
| **M** | Market & Customers | 12 | `M_Q1` – `M_Q12` | Customer Segments & Competitive Matrix (EBD3) |
| **PMF** | Product Market Fit | 34 | `PMF_Q1` – `PMF_Q34` | Customer Discovery Interviews Log |
| **T** | Team Targets | 31 | `T_Q1` – `T_Q31` | Hiring Plans, Targets & Milestone Tracking |
| **TP** | Tech / Product | 16 | `TP_Q1` – `TP_Q16` | Technology Validation (EBD4) |
| **TOTAL** | **10 Categories** | **282** | | **Standardized CleanTech Open Rubric** |

---

## Architecture & Directory Layout

```text
├── site/                       # Frontend web applications
│   ├── index.html              # Scorer & Judge evaluation workspace
│   ├── admin.html              # Cohort administrator & assignment dashboard
│   ├── css/                    # Modular stylesheets
│   └── js/                     # Application logic
│       ├── app.js              # State orchestration, modal handlers & API calls
│       ├── render.js           # Split-view DOM rendering & citation auto-jump
│       ├── scoring.js          # Progress calculation & score aggregation
│       ├── admin.js            # Assignment tables, progress charts & filters
│       └── export.js           # CSV/JSON audit and data export utilities
├── api/                        # Serverless edge functions (Netlify / Supabase)
│   ├── get-startup.js          # Hydrates startup payload and judge reviews
│   ├── save-score.js           # Debounced persistence for score & justification
│   └── list-startups.js        # Supplies queue listings to dashboards
├── scripts/                    # Automation & pipeline utilities
│   ├── generate_tutorials.py   # Headless Chrome generator for PDF manuals
│   └── extract_scaffolding_catalog.py # Cross-corpus scaffolding frequency analyzer
├── docs/                       # Documentation & generated guides
│   ├── CleanTech_Open_Scorer_Tutorial.pdf # Judge guidance manual (5 pages)
│   └── CleanTech_Open_Admin_Tutorial.pdf  # Admin operations manual (6 pages)
├── data/
│   ├── raw/                    # Raw founder deliverables and ground-truth CSVs
│   ├── ai_cache_clean/         # Local mirror of 93 clean extraction JSONs
│   └── MASTER_SCAFFOLDING_CATALOG.md # Documented competition template text
├── master_282_rubric.json      # Ground-truth 282-question diligence rubric
└── 13_push_clean_extractions_to_supabase.py # Reverse-indexing & database sync
```

---

## Quick Start & Local Development

### 1. Requirements
- Node.js (v18+)
- Python 3.10+ (with `psycopg2`, `pymupdf`)
- Google Chrome (for headless PDF generation)

### 2. Environment Setup
Create a `.env` file in the project root:
```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres
SUPABASE_URL=https://[PROJECT_ID].supabase.co
SUPABASE_ANON_KEY=[ANON_KEY]
```

### 3. Running the Web Application
```bash
# Serve the site directory locally
npx serve site
# Scorer portal: http://localhost:3000/index.html
# Admin dashboard: http://localhost:3000/admin.html
```

### 4. Compiling & Syncing PDF Manuals
```bash
python3 scripts/generate_tutorials.py
# Generates and syncs updated PDF manuals directly to your Desktop.
```
