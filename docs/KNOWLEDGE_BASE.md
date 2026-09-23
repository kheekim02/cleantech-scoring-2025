# CleanTech Open 2025 Diligence Engine — Comprehensive Knowledge Base

This document serves as the exhaustive architectural and operational reference for the CleanTech Open 2025 Diligence Engine platform.

---

## 1. System Architecture & Component Interactions

```
  ┌────────────────────────────────────────────────────────┐
  │                 Supabase PostgreSQL                   │
  │  - startup_extractions (JSONB payloads, citations)     │
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
  │  - Real-time Score Saving    │   │  - CSV Export & Auditing   │
  │  - Citation Auto-Jumping     │   │  - Clean Ready Filter      │
  └──────────────────────────────┘   └────────────────────────────┘
```

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

## 5. Frontend Navigation & Citation Auto-Jumping

### Side-by-Side Split Workspace
The scorer interface ([`site/index.html`](../site/index.html)) provides zero-tab-switching evaluation:
- **Left Panel (PDF Viewer)**: Embedded `<iframe id="pdf-frame">` with integrated browser controls, page selection, and a deliverable selector dropdown.
- **Right Panel (Criteria Cards)**:
  - Header: Category badge, criterion ID, AI suggestion pill (`⚡ 1.0 PT | 95% Conf`).
  - Text: Diligence prompt question.
  - Justification: Input field with `📄 View Examples` modal trigger.
  - Citation: Clickable `🔗 View AI Citation (p. X)` link.
  - Point Selector: `1 PT`, `0.75 PTS`, `0.5 PTS`, `0.25 PTS`, `0 PTS`.

### Citation Auto-Jump Mechanism
When a reviewer clicks `🔗 View AI Citation (p. X)`:
1. `site/js/app.js` captures click via event delegation.
2. Reads `dataset.pdf` and `dataset.page` from the citation element.
3. Invokes `CTO.Render.jumpToCitation(pdfFilename, pageNum)`:
   - Switches the deliverable dropdown to `pdfFilename`.
   - Appends `#page=X` to the iframe source.
   - Updates status caption: *"Switched viewer to Page X. Use Cmd+F / Ctrl+F in the viewer to locate exact text."*
