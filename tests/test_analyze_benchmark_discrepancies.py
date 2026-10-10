# tests/test_analyze_benchmark_discrepancies.py
import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_benchmark_discrepancies import (
    analyze_category_discrepancies,
    classify_error_modes,
    rank_worst_criteria,
)


class TestAnalyzeBenchmarkDiscrepancies(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp.name)
        (self.cache_dir / "A.json").write_text(json.dumps([
            {"q_id": "BC_Q1", "predicted_val": 1.0, "citation": "cite1"},
            {"q_id": "BC_Q2", "predicted_val": None, "citation": None, "error_code": "WITHHELD_UNGROUNDED"},
            {"q_id": "M_Q1", "predicted_val": 1.0, "citation": "cite2"},
            {"q_id": "M_Q2", "predicted_val": 0.0, "citation": None},
        ]))
        self.human_rows = [
            {"startup_id": "A", "question_id": "BC_Q1", "score": 0.5},
            {"startup_id": "A", "question_id": "BC_Q2", "score": 1.0},
            {"startup_id": "A", "question_id": "M_Q1", "score": 0.0},
            {"startup_id": "A", "question_id": "M_Q2", "score": 0.0},
        ]
        self.rubric = [
            {"new_q_id": "BC_Q1", "cat_code": "BC", "text": "Value Proposition"},
            {"new_q_id": "BC_Q2", "cat_code": "BC", "text": "Customer Segments"},
            {"new_q_id": "M_Q1", "cat_code": "M", "text": "Market Size"},
            {"new_q_id": "M_Q2", "cat_code": "M", "text": "Competitor Matrix"},
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_analyze_category_discrepancies(self):
        stats = analyze_category_discrepancies(self.cache_dir, self.human_rows, ["A"], self.rubric)
        self.assertIn("BC", stats)
        self.assertIn("M", stats)
        self.assertEqual(stats["BC"]["pairs"], 1)
        self.assertEqual(stats["BC"]["exact_count"], 0)
        self.assertAlmostEqual(stats["BC"]["mae"], 0.5)
        self.assertAlmostEqual(stats["BC"]["mean_bias"], 0.5)  # AI (1.0) - Human (0.5) = +0.5
        self.assertEqual(stats["BC"]["withheld_count"], 1)

        self.assertEqual(stats["M"]["pairs"], 2)
        self.assertEqual(stats["M"]["exact_count"], 1)
        self.assertAlmostEqual(stats["M"]["mae"], 0.5)

    def test_rank_worst_criteria(self):
        worst = rank_worst_criteria(self.cache_dir, self.human_rows, ["A"], self.rubric, top_k=2)
        self.assertEqual(len(worst), 2)
        self.assertEqual(worst[0]["q_id"], "M_Q1")  # MAE 1.0 (AI 1.0 vs Human 0.0)
        self.assertAlmostEqual(worst[0]["mae"], 1.0)
        self.assertEqual(worst[0]["exact_match_pct"], 0.0)

    def test_classify_error_modes(self):
        modes = classify_error_modes(self.cache_dir, self.human_rows, ["A"])
        # M_Q1: AI=1.0, Human=0.0 -> over_prediction
        # BC_Q1: AI=1.0, Human=0.5 -> fractional_tier_mismatch
        # BC_Q2: AI=None, Human=1.0 -> withheld
        # M_Q2: AI=0.0, Human=0.0 -> exact_match
        self.assertEqual(modes["exact_match"], 1)
        self.assertEqual(modes["over_prediction"], 1)
        self.assertEqual(modes["fractional_tier_mismatch"], 1)
        self.assertEqual(modes["withheld"], 1)

    def test_format_discrepancy_markdown(self):
        from scripts.analyze_benchmark_discrepancies import format_discrepancy_markdown
        cat_summary = {
            "BC": {"pairs": 10, "exact_match_pct": 50.0, "mae": 0.3, "mean_bias": 0.1, "withheld_pct": 20.0, "total_criteria": 12}
        }
        worst_q = [
            {"q_id": "BC_Q1", "cat_code": "BC", "text": "Value Prop", "pairs": 5, "mae": 0.6, "mean_bias": 0.2, "exact_match_pct": 40.0}
        ]
        modes = {"exact_match": 5, "over_prediction": 2, "under_prediction": 1, "fractional_tier_mismatch": 2, "withheld": 2}
        md = format_discrepancy_markdown(cat_summary, worst_q, modes, 12, {"source_host": "local", "path": "test"})
        self.assertIn("# Task 0 Benchmark Discrepancy Analysis", md)
        self.assertIn("| BC |", md)
        self.assertIn("BC_Q1", md)
        self.assertIn("Over-prediction", md)


if __name__ == "__main__":
    unittest.main()

