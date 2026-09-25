#!/usr/bin/env python3
"""
Phase 3: Independent Verifier (11_independent_verifier.py)
Validates mutated candidate prompts against anomaly targets and the Golden Dataset
to prevent regressions and verify real-world resolution.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple

class GoldenEntry:
    def __init__(self, data: Dict[str, Any]):
        self.startup = data['startup']
        self.q_id = data['q_id']
        self.min_score = data.get('min_score', 0.0)
        self.max_score = data.get('max_score', 1.0)
        self.citation_must_not_contain = data.get('citation_must_not_contain', [])
        self.rationale_must_not_contain = data.get('rationale_must_not_contain', [])
        self.rationale_must_contain = data.get('rationale_must_contain', [])
        self.citation_must_be_null = data.get('citation_must_be_null', False)
        self.notes = data.get('notes', '')

    def verify(self, output: Dict[str, Any]) -> Tuple[bool, str]:
        score = output.get('predicted_val')
        rat = output.get('rationale') or ''
        cit = output.get('citation')

        # Check score range
        if score is None or not (self.min_score <= score <= self.max_score):
            return False, f"Score {score} not in expected range [{self.min_score}, {self.max_score}]"

        # Check citation null constraint
        if self.citation_must_be_null and cit is not None:
            return False, f"Expected citation to be null, got: '{cit}'"

        # Check citation exclusions
        if cit:
            cit_lower = cit.lower()
            for forbidden in self.citation_must_not_contain:
                if forbidden.lower() in cit_lower:
                    return False, f"Citation contains forbidden string '{forbidden}'"

        # Check rationale exclusions
        rat_lower = rat.lower()
        for forbidden in self.rationale_must_not_contain:
            if forbidden.lower() in rat_lower:
                return False, f"Rationale contains forbidden string '{forbidden}'"

        # Check rationale requirements
        for required in self.rationale_must_contain:
            if required.lower() not in rat_lower:
                return False, f"Rationale missing required string '{required}'"

        return True, "PASSED"

class IndependentVerifier:
    def __init__(self, golden_dataset_path: str, raw_base_dir: str = '/data/scraping/datasets/cto_accelerator/parsed_clean'):
        self.golden_path = golden_dataset_path
        self.raw_base_dir = raw_base_dir
        self.golden_dataset: List[GoldenEntry] = self.load_golden()

    def load_golden(self) -> List[GoldenEntry]:
        if not os.path.exists(self.golden_path):
            return []
        with open(self.golden_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [GoldenEntry(entry) for entry in data]

    def add_to_golden(self, new_entry_data: Dict[str, Any]) -> None:
        self.golden_dataset.append(GoldenEntry(new_entry_data))
        raw_list = [
            {
                "startup": e.startup,
                "q_id": e.q_id,
                "min_score": e.min_score,
                "max_score": e.max_score,
                "citation_must_not_contain": e.citation_must_not_contain,
                "rationale_must_not_contain": e.rationale_must_not_contain,
                "rationale_must_contain": e.rationale_must_contain,
                "citation_must_be_null": e.citation_must_be_null,
                "notes": e.notes
            }
            for e in self.golden_dataset
        ]
        with open(self.golden_path, 'w', encoding='utf-8') as f:
            json.dump(raw_list, f, indent=2)

    def get_document_text(self, company: str, q_id: str) -> str:
        cat_dir = os.path.join(self.raw_base_dir, company, 'converted')
        if not os.path.exists(cat_dir):
            return ""

        cat_code = q_id.split('_')[0]
        cat_patterns = {
            'BC': [r'Canvas', r'EBD3', r'M3'],
            'ES': [r'Executive_Summary', r'EBD1', r'Summary'],
            'IS': [r'EBD2', r'M2', r'GHG', r'Inclusion'],
            'M': [r'M4', r'EBD3', r'Customer'],
            'PMF': [r'M3', r'M1', r'CustomerDiscovery', r'Canvas'],
            'TP': [r'EBD4', r'TechnologyValidation', r'Patent'],
            'F': [r'M6', r'FinancialProjection', r'Financ'],
            'T': [r'M8', r'Team', r'Targets'],
            'IP': [r'Pitch', r'Deck', r'Investor', r'EBD8'],
            'L': [r'M7', r'Inclusion', r'Legal', r'Patent']
        }

        all_files = [f for f in os.listdir(cat_dir) if f.endswith('.md')]
        patterns = cat_patterns.get(cat_code, [])

        priority_files = []
        other_files = []
        for f in all_files:
            if any(re.search(p, f, re.IGNORECASE) for p in patterns):
                priority_files.append(f)
            else:
                other_files.append(f)

        text_blocks = []
        for f in priority_files + other_files:
            with open(os.path.join(cat_dir, f), 'r', errors='ignore') as file:
                text_blocks.append(f"\n--- SOURCE DOCUMENT: {f} ---\n" + file.read())

        return "\n".join(text_blocks)

    def verify_candidate(
        self,
        extractor_fn,
        anomaly_target: Dict[str, Any],
        rubric_map: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes full Phase 3 verification:
        1. Tests candidate against anomaly target.
        2. Tests candidate against all Golden Dataset regression entries.
        """
        company = anomaly_target['company']
        q_id = anomaly_target['q_id']
        q_meta = rubric_map.get(q_id)
        if not q_meta:
            return False, f"Question {q_id} not found in rubric.", {}

        # 1. Test against anomaly target
        target_doc = self.get_document_text(company, q_id)
        new_output = extractor_fn(q_meta, target_doc)

        new_val = new_output.get('predicted_val')
        new_cit = new_output.get('citation')
        new_rat = new_output.get('rationale') or ''

        # Sanity checks on target output
        if new_val is None:
            return False, f"Target test produced None score for {company} {q_id}", new_output

        if new_val == 0.0 and new_cit:
            return False, f"Target test violated nullification on zero score: cit='{new_cit}'", new_output

        # 2. Test against all Golden Dataset entries (Anti-Regression Gate)
        for g_entry in self.golden_dataset:
            g_q_meta = rubric_map.get(g_entry.q_id)
            if not g_q_meta:
                continue
            g_doc = self.get_document_text(g_entry.startup, g_entry.q_id)
            g_out = extractor_fn(g_q_meta, g_doc)

            passed, reason = g_entry.verify(g_out)
            if not passed:
                return False, f"Regression on Golden Entry ({g_entry.startup} - {g_entry.q_id}): {reason}", new_output

        return True, "All Golden Dataset regression tests and anomaly checks passed.", new_output

if __name__ == '__main__':
    verifier = IndependentVerifier('/data/scraping/datasets/cto_accelerator/golden_dataset.json')
    print(f"Loaded {len(verifier.golden_dataset)} golden dataset regression entries.")
