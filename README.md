# Startup Scorer Engine (MVP)

A data-driven diligence and triage engine for boutique investment bankers, corporate VCs, and accelerators.

## Project Structure
- `data/raw/`: Original evaluation rubrics (954 startups) and longitudinal outcomes (Spring 2026).
- `data/processed/`: Cleaned, unified datasets and scoring benchmarks.
- `src/ingestion/`: Multi-format parsers (PDFs, Excel spreadsheets, video transcripts).
- `src/models/`: Optimized 10-category scoring algorithm and survival/funding predictive models.
- `src/pipeline/`: Automated deal intake and 1-Page Investment Memo generator.
- `scripts/`: CLI utilities to score incoming deals and run statistical backtests.

## Quick Start
```bash
pip install -r requirements.txt
python scripts/run_analysis.py
```
