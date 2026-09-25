#!/usr/bin/env python3
"""
Phase 2 & 3 Master Orchestrator (12_optimization_loop.py)
Automates the prompt optimization and verification cycle across all flagged anomalies.
Integrates:
- Anomaly report ingestion
- Failure classification & deduplication
- Rule Decoction & Prompt Mutation (Phase 2)
- Anti-Regression Golden Dataset Verification (Phase 3)
- 3-Attempt Circuit Breakers & Pre-Coded Strategy Escalation (A -> B -> C)
- Production script promotion & Golden Dataset ratcheting
"""

import os
import sys
import json
import time
import importlib
from typing import Dict, Any, List

# Dynamic imports for numbered script files
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
opt_mod = importlib.import_module("10_prompt_optimizer")
ver_mod = importlib.import_module("11_independent_verifier")
strat_mod = importlib.import_module("prompt_strategies")

AnomalyRecord = opt_mod.AnomalyRecord
parse_anomaly_report = opt_mod.parse_anomaly_report
PromptOptimizer = opt_mod.PromptOptimizer
IndependentVerifier = ver_mod.IndependentVerifier

# Paths
ANOMALY_REPORT_PATH = '/data/scraping/datasets/cto_accelerator/semantic_flagged_responses.md'
GOLDEN_DATASET_PATH = '/data/scraping/datasets/cto_accelerator/golden_dataset.json'
PRODUCTION_SCRIPT_PATH = '/data/scraping/datasets/cto_accelerator/08_ai_copilot_extractor_strict.py'
CANDIDATE_SCRIPT_PATH = '/data/scraping/datasets/cto_accelerator/08_ai_copilot_extractor_strict_candidate.py'
RUBRIC_PATH = '/data/scraping/datasets/cto_accelerator/master_282_rubric.json'
FINAL_REPORT_PATH = '/data/scraping/datasets/cto_accelerator/optimization_report.md'

def load_rubric(rubric_path: str) -> Dict[str, Any]:
    # Fallback to local if remote path doesn't exist
    if not os.path.exists(rubric_path):
        rubric_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'master_282_rubric.json')
    with open(rubric_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return {q.get('new_q_id', q.get('q_id')): q for q in data}

def deduplicate_anomalies(records: List[AnomalyRecord]) -> List[AnomalyRecord]:
    """
    Groups anomalies by (q_id, failure_mode) to ensure prompt mutations
    target general root causes rather than repeating work on identical issues.
    """
    seen = set()
    unique = []
    for r in records:
        key = (r.q_id, r.failure_mode)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

def run_loop():
    print("=" * 60)
    print("STARTING AI-AS-A-JUDGE PROMPT OPTIMIZATION LOOP (PHASE 2 & 3)")
    print("=" * 60)

    if not os.path.exists(ANOMALY_REPORT_PATH):
        print(f"Anomaly report not found at {ANOMALY_REPORT_PATH}.")
        print("Ensure Phase 1 (09_semantic_critic.py) has completed its scan.")
        return

    records = parse_anomaly_report(ANOMALY_REPORT_PATH)
    print(f"Loaded {len(records)} raw anomalies from report.")
    unique_issues = deduplicate_anomalies(records)
    print(f"Deduplicated to {len(unique_issues)} unique conceptual targets.")

    rubric_map = load_rubric(RUBRIC_PATH)
    verifier = IndependentVerifier(GOLDEN_DATASET_PATH)
    print(f"Initialized Verifier with {len(verifier.golden_dataset)} golden regression benchmarks.")

    committed_rules = list(strat_mod.DEFAULT_RULES)
    committed_rewrites = dict(strat_mod.DEFAULT_QUESTION_REWRITES)

    results = {
        "committed": [],
        "human_intervention_required": [],
        "skipped": []
    }

    for idx, issue in enumerate(unique_issues, 1):
        print(f"\n[{idx}/{len(unique_issues)}] Processing Target: {issue.company} - {issue.q_id} ({issue.failure_mode})")

        strategies = ["A", "B", "C"]
        resolved = False

        for strategy in strategies:
            if resolved:
                break

            print(f"  --> Testing Strategy {strategy}...")
            attempts = 0
            MAX_ATTEMPTS = 3

            while attempts < MAX_ATTEMPTS and not resolved:
                attempts += 1
                # Fresh fork from committed baseline state
                optimizer = PromptOptimizer(base_rules=committed_rules, question_rewrites=committed_rewrites)
                fix_level = min(attempts, 3)
                mutation_info = optimizer.optimize_for_record(issue, level=fix_level)
                print(f"    [Attempt {attempts} - Level {fix_level}] Applied: {mutation_info['action']}")

                # Build candidate execution function
                def candidate_extractor(q_meta, doc_text):
                    if strategy == "A":
                        return strat_mod.execute_strategy_a(
                            q_meta, doc_text,
                            rules=optimizer.rules,
                            rewrites=optimizer.rewrites,
                            few_shot_examples=optimizer.few_shot_examples.get(q_meta.get('new_q_id', q_meta.get('q_id')))
                        )
                    elif strategy == "B":
                        return strat_mod.execute_strategy_b(
                            q_meta, doc_text,
                            rules=optimizer.rules,
                            rewrites=optimizer.rewrites
                        )
                    elif strategy == "C":
                        return strat_mod.execute_strategy_c(
                            q_meta, doc_text,
                            rewrites=optimizer.rewrites
                        )

                # Phase 3 Independent Verification
                passed, reason, new_output = verifier.verify_candidate(
                    candidate_extractor,
                    issue.to_dict(),
                    rubric_map
                )

                if passed:
                    print(f"    ✅ VERIFICATION PASSED: {reason}")
                    # Export candidate script and promote to production
                    if os.path.exists(PRODUCTION_SCRIPT_PATH):
                        optimizer.export_candidate_script(PRODUCTION_SCRIPT_PATH, CANDIDATE_SCRIPT_PATH)
                        os.replace(CANDIDATE_SCRIPT_PATH, PRODUCTION_SCRIPT_PATH)

                    # Advance committed baseline state
                    committed_rules = list(optimizer.rules)
                    committed_rewrites = dict(optimizer.rewrites)

                    # Add to Golden Dataset (Ratchet forward)
                    new_val = new_output.get('predicted_val', 0.0)
                    verifier.add_to_golden({
                        "startup": issue.company,
                        "q_id": issue.q_id,
                        "min_score": max(0.0, new_val - 0.25),
                        "max_score": min(1.0, new_val + 0.25),
                        "citation_must_not_contain": [issue.citation] if issue.failure_mode == "HALLUCINATED_CITATION" and issue.citation else [],
                        "rationale_must_not_contain": [],
                        "rationale_must_contain": [],
                        "citation_must_be_null": True if new_val == 0.0 else False,
                        "notes": f"Auto-ratcheted from resolved anomaly ({issue.failure_mode})"
                    })

                    results["committed"].append({
                        "company": issue.company,
                        "q_id": issue.q_id,
                        "failure_mode": issue.failure_mode,
                        "strategy": strategy,
                        "attempts": attempts,
                        "action": mutation_info["action"]
                    })
                    resolved = True
                    break
                else:
                    print(f"    ❌ VERIFICATION FAILED: {reason}")

            if not resolved:
                print(f"  ⚠️ Strategy {strategy} failed after {MAX_ATTEMPTS} attempts. Escalating...")

        if not resolved:
            print(f"  🚨 ALL STRATEGIES EXHAUSTED FOR {issue.company} - {issue.q_id}. Tripping Circuit Breaker.")
            results["human_intervention_required"].append(issue.to_dict())

    # Write summary report
    print("\n" + "=" * 60)
    print("OPTIMIZATION LOOP COMPLETE. Writing final audit report...")
    print("=" * 60)
    with open(FINAL_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("# Automated AI-as-a-Judge Optimization Report\n\n")
        f.write(f"- Total Anomalies Evaluated: {len(unique_issues)}\n")
        f.write(f"- Successfully Committed Mutations: {len(results['committed'])}\n")
        f.write(f"- Human Intervention Required: {len(results['human_intervention_required'])}\n\n")

        f.write("## Committed Prompt Mutations\n\n")
        for c in results['committed']:
            f.write(f"### {c['company']} - {c['q_id']}\n")
            f.write(f"- **Failure Mode:** {c['failure_mode']}\n")
            f.write(f"- **Winning Strategy:** Strategy {c['strategy']}\n")
            f.write(f"- **Iterations:** {c['attempts']}\n")
            f.write(f"- **Action:** {c['action']}\n\n")

        if results['human_intervention_required']:
            f.write("## ⚠️ Human Intervention Required\n\n")
            for h in results['human_intervention_required']:
                f.write(f"### {h['company']} - {h['q_id']}\n")
                f.write(f"- **Failure Mode:** {h['failure_mode']}\n")
                f.write(f"- **Anomaly Details:** {h['anomaly_type']}\n")
                f.write(f"- **Recorded Score:** {h['score']}\n")
                f.write(f"- **Recorded Rationale:** {h['rationale']}\n\n")

    print(f"Final report saved to {FINAL_REPORT_PATH}")

if __name__ == '__main__':
    run_loop()
