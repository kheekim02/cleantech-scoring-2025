# Startup Scorer AI Workspace Rules & Protocol

This file defines the engineering protocols, prompting standards, and hallucination-reduction safeguards for all AI models working within this repository.

---

## 1. Core Operating Principles

1. **Zero Hallucination Tolerance on Data:**
   - Never invent financial numbers, valuation multiples, patent counts, or founder pedigree.
   - If an artifact (PDF, spreadsheet, transcript) lacks information for a rubric question, explicitly output `"STATUS: INSUFFICIENT_DATA"`. Never guess.

2. **Grounded Extraction (Verbatim Citation Requirement):**
   - Every score or qualitative claim extracted from a startup document MUST be backed by a verbatim text snippet (`<source_quote>`) and document name/page number.

3. **Deterministic Structure (XML + JSON):**
   - Use XML tags (`<context>`, `<rubric>`, `<thinking>`, `<output>`) to strictly separate instructions from raw startup documents.
   - Machine-readable outputs must be strict, valid JSON conforming to defined Pydantic schemas.

4. **Token Efficiency & Prompt Caching:**
   - Keep static system prompts, 10-category rubrics, and few-shot calibration examples at the TOP of the prompt context to maximize KV-cache reuse.
   - Place variable startup documents at the BOTTOM.

---

## 2. Directory Architecture
- `data/raw/`: Read-only ground-truth files (Cleaned scores, outcomes CSV, question rubrics).
- `data/processed/`: Standardized, entity-resolved datasets.
- `src/ingestion/`: Multi-format parsers (PDF, Excel, Video markdown).
- `src/models/`: Scoring algorithms and survival classifiers.
- `src/pipeline/`: End-to-end deal intake and memo generators.

---

## 3. Evaluation Standards
- **High-Conviction Weights:** Prioritize Tech & Product (25%), Business Canvas (20%), Pitch (15%), and Financials (15%).
- **Objective vs Subjective:**
  - Objective (1): Deterministic extraction (patent filings, revenue timelines, 3rd-party lab validation).
  - Subjective (0): Scored with few-shot calibration and confidence scores (0.0 - 1.0). If confidence < 0.70, flag for Human-in-the-Loop review.
