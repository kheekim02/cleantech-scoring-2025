#!/usr/bin/env python3
"""
Deterministic Verbatim Grounding Filter (13_ground_citations.py)

Sweeps through all 94 cached extraction JSONs and applies a strict
verbatim verification against the source documents:

- KEEPS citations that exist (even partially) in the source document,
  regardless of the score. A 0.0 score with a real founder quote is
  valuable context for judges.
- NULLIFIES only citations that are LLM analytical commentary
  (fabricated text that doesn't exist in the source).

No LLM calls required. Pure string matching with OCR-tolerant fuzzy fallback.
"""

import os
import sys
import re
import json
import time
from typing import Optional

import argparse

# Ground the shadow generation against the cleaned v4 tree. These defaults
# refuse the shipped cache and the previous cleaned tree.
DEFAULT_CACHE_DIR = '/data/scraping/datasets/cto_accelerator/ai_cache_v4_shadow'
DEFAULT_PARSED_DIR = '/data/scraping/datasets/cto_accelerator/parsed_clean_v4'
DEFAULT_REPORT = '/data/scraping/datasets/cto_accelerator/grounding_report_v4.md'
PRODUCTION_CACHE = 'ai_cache_v3_strict'
PREVIOUS_PARSED = 'parsed_clean'

# Patterns that indicate the LLM wrote analytical commentary, not a verbatim quote
LLM_COMMENTARY_PREFIXES = [
    "the document does not",
    "the document doesn't",
    "the document mentions",
    "the document provides",
    "the document states",
    "the document only",
    "the document lacks",
    "the founder does not",
    "the founder doesn't",
    "the founder mentions",
    "the founder provides",
    "the founder lists",
    "the founder states",
    "the presentation does not",
    "the presentation depicts",
    "the presentation provides",
    "the presentation shows",
    "the presentation mentions",
    "the bmc sections",
    "the bmc does not",
    "the business model canvas",
    "although the document",
    "although the founder",
    "although the text",
    "no explicit mention",
    "no explicit evidence",
    "there is no explicit",
    "the text does not",
    "the startup does not",
    "the company does not",
    "while the document",
    "while the founder",
    "the executive summary does not",
    "the financial projections do not",
    "the pitch deck does not",
]

def normalize(text: str) -> str:
    """Normalize whitespace, case, and common OCR artifacts for comparison."""
    text = text.lower()
    text = re.sub(r'<[^>]+>', ' ', text)        # Strip HTML tags
    text = re.sub(r'[^\w\s.,;:!?\'-]', ' ', text)  # Keep basic punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_all_doc_text(cat_dir: str) -> str:
    """Load ALL documents in the converted directory for broad matching."""
    if not os.path.exists(cat_dir):
        return ""
    text_blocks = []
    for f in sorted(os.listdir(cat_dir)):
        if f.endswith('.md'):
            with open(os.path.join(cat_dir, f), 'r', errors='ignore') as fh:
                text_blocks.append(fh.read())
    return "\n".join(text_blocks)

def is_llm_commentary(citation: str) -> bool:
    """Check if citation starts with known LLM analytical commentary patterns."""
    cit_lower = citation.lower().strip()
    return any(cit_lower.startswith(prefix) for prefix in LLM_COMMENTARY_PREFIXES)

def verify_citation_verbatim(citation: str, doc_text_normalized: str) -> bool:
    """
    Multi-tier verbatim verification:
    1. Exact normalized match (full citation)
    2. 40-char prefix match (handles truncation)
    3. 8-word prefix match (handles OCR line-break artifacts)
    """
    cit_norm = normalize(citation)

    if len(cit_norm) < 10:
        return False  # Too short to be meaningful

    # Tier 1: Full normalized substring match
    if cit_norm in doc_text_normalized:
        return True

    # Tier 2: First 40 normalized characters match
    if len(cit_norm) >= 40 and cit_norm[:40] in doc_text_normalized:
        return True

    # Tier 3: First 8 words match (OCR-tolerant)
    words = cit_norm.split()
    if len(words) >= 8:
        prefix_8 = ' '.join(words[:8])
        if prefix_8 in doc_text_normalized:
            return True

    # Tier 4: First 5 words match (very forgiving for short citations)
    if len(words) >= 5:
        prefix_5 = ' '.join(words[:5])
        if len(prefix_5) > 15 and prefix_5 in doc_text_normalized:
            return True

    return False

def refuse_production_path(path: str, banned_name: str) -> None:
    """Stop before a run can rewrite the shipped cache or the previous cleaned tree."""
    norm = os.path.abspath(path).rstrip(os.sep)
    if os.path.basename(norm) == banned_name:
        raise SystemExit(f"Refusing production path {norm}")


def ground_citations(cache_dir: str, parsed_dir: str, report_path: str) -> None:
    print("=" * 60)
    print("DETERMINISTIC VERBATIM GROUNDING FILTER")
    print("=" * 60)

    stats = {
        'total_citations': 0,
        'kept_verbatim': 0,
        'nullified_commentary': 0,
        'nullified_fabricated': 0,
        'files_processed': 0,
    }

    log_entries = []

    if not os.path.isdir(cache_dir):
        raise SystemExit(f"Shadow cache is missing: {cache_dir}")

    for filename in sorted(os.listdir(cache_dir)):
        if not filename.endswith('.json'):
            continue

        company = filename.replace('.json', '')
        filepath = os.path.join(cache_dir, filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception:
                continue

        # Load ALL source documents for this company (not just category-specific)
        cat_dir = os.path.join(parsed_dir, company, 'converted')
        full_doc_text = get_all_doc_text(cat_dir)
        doc_normalized = normalize(full_doc_text)

        modified = False

        for item in data:
            cit = item.get('citation')
            if not cit or cit.lower() in ('null', 'none', 'n/a'):
                continue

            stats['total_citations'] += 1
            q_id = item.get('q_id', '?')
            val = item.get('predicted_val')

            # Step 1: Check for LLM commentary patterns
            if is_llm_commentary(cit):
                log_entries.append({
                    'company': company,
                    'q_id': q_id,
                    'score': val,
                    'action': 'NULLIFIED (LLM Commentary)',
                    'citation': cit[:120]
                })
                item['citation'] = None
                stats['nullified_commentary'] += 1
                modified = True
                continue

            # Step 2: Verbatim verification against source documents
            if verify_citation_verbatim(cit, doc_normalized):
                stats['kept_verbatim'] += 1
                continue  # Citation is real, keep it regardless of score

            # Step 3: Citation not found in source — fabricated
            log_entries.append({
                'company': company,
                'q_id': q_id,
                'score': val,
                'action': 'NULLIFIED (Not Found in Source)',
                'citation': cit[:120]
            })
            item['citation'] = None
            stats['nullified_fabricated'] += 1
            modified = True

        if modified:
            tmp_path = filepath + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, filepath)

        stats['files_processed'] += 1
        if stats['files_processed'] % 10 == 0:
            print(f"  Processed {stats['files_processed']} files...", flush=True)

    # Write grounding report
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Deterministic Verbatim Grounding Report\n\n")
        f.write(f"- **Total Citations Evaluated:** {stats['total_citations']}\n")
        f.write(f"- **Kept (Verbatim Match):** {stats['kept_verbatim']}\n")
        f.write(f"- **Nullified (LLM Commentary):** {stats['nullified_commentary']}\n")
        f.write(f"- **Nullified (Fabricated / Not in Source):** {stats['nullified_fabricated']}\n")
        f.write(f"- **Files Processed:** {stats['files_processed']}\n\n")

        if log_entries:
            f.write("## Nullified Citations Log\n\n")
            for entry in log_entries:
                f.write(f"### {entry['company']} — {entry['q_id']} (Score: {entry['score']})\n")
                f.write(f"- **Action:** {entry['action']}\n")
                f.write(f"- **Citation:** {entry['citation']}...\n\n")

    print("\n" + "=" * 60)
    print("GROUNDING COMPLETE")
    print(f"  Total Citations:       {stats['total_citations']}")
    print(f"  Kept (Verbatim):       {stats['kept_verbatim']}")
    print(f"  Nullified (Commentary):{stats['nullified_commentary']}")
    print(f"  Nullified (Fabricated):{stats['nullified_fabricated']}")
    print(f"  Report: {report_path}")
    print("=" * 60)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Ground shadow-cache citations against parsed_clean_v4.")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    parser.add_argument("--parsed-dir", default=DEFAULT_PARSED_DIR)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    refuse_production_path(args.cache_dir, PRODUCTION_CACHE)
    refuse_production_path(args.parsed_dir, PREVIOUS_PARSED)
    ground_citations(args.cache_dir, args.parsed_dir, args.report)


if __name__ == '__main__':
    main()
