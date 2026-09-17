# Prompt Engineering & Grounding Standards

## 1. The XML Tagging Hierarchy
Anthropic and frontier LLM architectures optimize attention across XML tags:
- `<system_prompt>`: High-level identity and core constraints.
- `<rubric>`: Formal definition of the 10 scoring categories and point ranges.
- `<documents>`: Raw parsed markdown from pitch decks, financial sheets, and videos.
- `<thinking>`: Mandatory chain-of-thought scratchpad where the model analyzes quotes before scoring.
- `<output_json>`: Strict machine-parseable response.

## 2. Hallucination Reduction Checklist
- [x] **Explicit "Don't Know" fallback:** Direct instruction to output `INSUFFICIENT_DATA` if absent.
- [x] **Quote extraction:** Model must emit `<source_quote>` before determining score.
- [x] **Two-Pass Verification:** Compare the score against the few-shot calibration table.
- [x] **Confidence Scoring:** Every metric includes a 0.0-1.0 confidence float.
