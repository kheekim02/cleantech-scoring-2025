#!/usr/bin/env python3
"""
Phase 2: Automated Prompt Optimizer (10_prompt_optimizer.py)
Ingests the anomaly report, classifies failure modes, performs Rule Decoction,
and generates targeted prompt mutations and candidate scripts.
"""

import os
import re
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typing import Dict, Any, List, Optional, Tuple

class AnomalyRecord:
    def __init__(self, company: str, q_id: str, anomaly_type: str, score: Optional[float], rationale: str, citation: Optional[str]):
        self.company = company
        self.q_id = q_id
        self.anomaly_type = anomaly_type
        self.score = score
        self.rationale = rationale
        self.citation = citation
        self.failure_mode = self.classify()

    def classify(self) -> str:
        cit_str = (self.citation or "").lower()
        rat_str = (self.rationale or "").lower()
        anom_str = (self.anomaly_type or "").lower()

        # Check for Rubric Contamination
        if any(w in cit_str for w in ["rubric_examples", "example for 1 pt", "mid-sized municipal wastewater"]):
            return "RUBRIC_CONTAMINATION"

        # Check for Scaffolding Leakage
        scaffold_indicators = [
            "instruction", "teamname_", "upload this document", "do not duplicate",
            "scoring guidelines", "evaluator notes", "template placeholder"
        ]
        if any(w in cit_str for w in scaffold_indicators):
            return "SCAFFOLD_LEAKAGE"

        # Check for Framework Literalism
        if any(w in rat_str for w in ["no bcg grid", "didn't provide a matrix", "no benefits matrix", "lack of explicit framework"]):
            return "FRAMEWORK_LITERALISM"

        # Check for Abstract Phrasing Penalty
        if any(w in rat_str for w in ["does not explicitly state the breadth", "did not use the word", "fails to mention breadth"]):
            return "ABSTRACT_PHRASING_PENALTY"

        # Check for Score-Rationale Contradiction
        if self.score is not None:
            if self.score >= 1.0 and ("does not explicitly state" in rat_str or "failed to provide" in rat_str or "lacks" in rat_str):
                return "SCORE_RATIONALE_CONTRADICTION"
            if self.score == 0.0 and ("explicitly states" in rat_str and "does not" not in rat_str):
                return "SCORE_RATIONALE_CONTRADICTION"

        # Check for Hallucinated Citation
        if "semantic citation hallucination" in anom_str or "failed llm verification" in anom_str:
            return "HALLUCINATED_CITATION"

        # Generic Rationale
        if len(rat_str) < 40 or "lacks concrete evidence" in rat_str:
            return "GENERIC_RATIONALE"

        return "HALLUCINATED_CITATION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company,
            "q_id": self.q_id,
            "anomaly_type": self.anomaly_type,
            "failure_mode": self.failure_mode,
            "score": self.score,
            "rationale": self.rationale,
            "citation": self.citation
        }

def parse_anomaly_report(report_path: str) -> List[AnomalyRecord]:
    if not os.path.exists(report_path):
        return []

    with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    records = []
    # Pattern matching "### Company - Q_ID" blocks
    blocks = re.split(r'###\s+', content)
    for block in blocks[1:]:
        lines = block.strip().split('\n')
        header = lines[0].strip()
        if ' - ' not in header:
            continue
        company, q_id = header.split(' - ', 1)
        company = company.strip()
        q_id = q_id.strip()

        anomaly_type = ""
        score = None
        rationale = ""
        citation = None

        for line in lines[1:]:
            line = line.strip()
            if line.startswith('- 🔴 **Anomaly:**'):
                anomaly_type = line.replace('- 🔴 **Anomaly:**', '').strip()
            elif line.startswith('- **Score:**'):
                raw_score = line.replace('- **Score:**', '').strip()
                try:
                    score = float(raw_score)
                except ValueError:
                    score = None
            elif line.startswith('- **Rationale:**'):
                rationale = line.replace('- **Rationale:**', '').strip()
            elif line.startswith('- **Citation:**'):
                cit_val = line.replace('- **Citation:**', '').strip()
                citation = None if cit_val.lower() == 'none' or cit_val.lower() == 'null' else cit_val

        records.append(AnomalyRecord(company, q_id, anomaly_type, score, rationale, citation))

    return records

class PromptOptimizer:
    def __init__(self, base_rules: Optional[List[str]] = None, question_rewrites: Optional[Dict[str, str]] = None):
        from prompt_strategies import DEFAULT_RULES, DEFAULT_QUESTION_REWRITES
        self.rules = list(base_rules or DEFAULT_RULES)
        self.rewrites = dict(question_rewrites or DEFAULT_QUESTION_REWRITES)
        self.few_shot_examples: Dict[str, str] = {}
        self.mutation_log: List[Dict[str, Any]] = []

    def decoct_rules(self) -> None:
        """
        Enforces Rule Decoction: Ensures rule count <= 10.
        Consolidates framework, abstraction, and phrasing rules if cap is exceeded.
        """
        if len(self.rules) <= 10:
            return

        # Consolidation map: merge literalism rules (Rules 5 & 8)
        consolidated = []
        merged_literalism = (
            "5. Agnosticism & Deductive Equivalence (CRITICAL): The rubric frequently references specific frameworks "
            "(e.g., BCG grid, benefits matrix) or abstract terminology (e.g., 'breadth of capabilities'). "
            "You MUST treat these as non-exclusive functional goals. If the founder provides ANY concrete analysis, "
            "feature comparison, or lists department roles (e.g., Technical, Sales, Finance), you MUST award full points. "
            "Never penalize for missing literal grid drawings or absent summary buzzwords."
        )
        has_merged = False
        for r in self.rules:
            if "Framework Agnosticism" in r or "Abstract Phrasing Agnosticism" in r:
                if not has_merged:
                    consolidated.append(merged_literalism)
                    has_merged = True
            else:
                consolidated.append(r)

        # Renumber rules sequentially
        renumbered = []
        for idx, r in enumerate(consolidated, 1):
            cleaned = re.sub(r'^\d+\.\s*', '', r)
            renumbered.append(f"{idx}. {cleaned}")

        self.rules = renumbered[:10]

    def optimize_for_record(self, record: AnomalyRecord, level: int = 1) -> Dict[str, Any]:
        """
        Applies fix technique according to level (1: Reinforce, 2: Rewrite, 3: Few-Shot, 4: Escalate).
        """
        mutation = {
            "target": {"company": record.company, "q_id": record.q_id},
            "failure_mode": record.failure_mode,
            "level": level,
            "action": None
        }

        if level == 1:
            # Level 1: Rule Reinforcement
            if record.failure_mode == "HALLUCINATED_CITATION":
                new_rule = f"Never invent citations. If extracted text is not verified verbatim in the text, citation must be null."
                self.rules.append(f"{len(self.rules) + 1}. Citation Grounding: {new_rule}")
                mutation["action"] = "Appended strict verbatim citation rule"
            elif record.failure_mode == "SCAFFOLD_LEAKAGE":
                new_rule = f"Template Boilerplate Exclusion: Do not extract text containing competition headers, instructions, or template prompts."
                self.rules.append(f"{len(self.rules) + 1}. Boilerplate Exclusion: {new_rule}")
                mutation["action"] = "Appended template boilerplate exclusion rule"
            elif record.failure_mode == "SCORE_RATIONALE_CONTRADICTION":
                mutation["action"] = "Reinforced score-rationale consistency clause"

            self.decoct_rules()

        elif level == 2:
            # Level 2: Question Text Rewrite
            if record.failure_mode in ["FRAMEWORK_LITERALISM", "ABSTRACT_PHRASING_PENALTY"]:
                new_text = f"Does the document provide concrete evidence, data, or operational details addressing {record.q_id}?"
                self.rewrites[record.q_id] = new_text
                mutation["action"] = f"Rewrote question {record.q_id} text to focus on substance over format"
            else:
                mutation["action"] = f"Maintained substantive rewrite for {record.q_id}"

        elif level == 3:
            # Level 3: Few-Shot Example Injection
            clean_example = (
                f"Question: {record.q_id}\n"
                f"Negative Example (DO NOT DO): Rationale claiming missing framework despite concrete text.\n"
                f"Positive Example (CORRECT): Read the founder text, identify concrete claims, award fractional/full points without demanding literal terminology."
            )
            self.few_shot_examples[record.q_id] = clean_example
            mutation["action"] = f"Added 1-shot calibration example for {record.q_id}"

        elif level >= 4:
            mutation["action"] = "Escalate to Strategy B (Chain-of-Thought) or Strategy C (Debate)"

        self.mutation_log.append(mutation)
        return mutation

    def export_candidate_script(self, template_path: str, candidate_output_path: str) -> None:
        """
        Creates 08_ai_copilot_extractor_strict_candidate.py with the mutated rules and rewrites.
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template script {template_path} not found.")

        with open(template_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Update Question Rewrites (handles first pass and subsequent passes cleanly)
        rewrites_code = "    # DYNAMIC QUESTION REWRITES (AUTO-GENERATED)\n"
        for q_id, rw_text in self.rewrites.items():
            rewrites_code += f'    if q_id == "{q_id}":\n        q_simple["text"] = "{rw_text}"\n'

        code = re.sub(
            r'    # (?:REWRITE BC QUESTIONS TO PREVENT LITERALISM|DYNAMIC QUESTION REWRITES \(AUTO-GENERATED\)).*?(?=\n    prompt =)',
            rewrites_code,
            code,
            flags=re.DOTALL
        )

        # Update Hard Fail Constraints
        rules_text = "\n".join(self.rules)
        code = re.sub(
            r'HARD FAIL CONSTRAINTS & STRICT GRADING RULES:\n.*?(?=\n\"\"\"\s*\n\s*res\s*=)',
            f'HARD FAIL CONSTRAINTS & STRICT GRADING RULES:\n{rules_text}',
            code,
            flags=re.DOTALL
        )

        with open(candidate_output_path, 'w', encoding='utf-8') as f:
            f.write(code)

if __name__ == '__main__':
    report_file = '/data/scraping/datasets/cto_accelerator/semantic_flagged_responses.md'
    records = parse_anomaly_report(report_file)
    print(f"Parsed {len(records)} anomalies from {report_file}")
    if records:
        print("Sample failure mode distribution:")
        distribution: Dict[str, int] = {}
        for r in records:
            distribution[r.failure_mode] = distribution.get(r.failure_mode, 0) + 1
        for mode, count in distribution.items():
            print(f"  {mode}: {count}")
