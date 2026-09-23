"""Unit tests for audit_v1_vs_v2_extractions comparison metrics."""
import unittest


class TestAuditMetrics(unittest.TestCase):
    def test_01_compute_concordance(self):
        """Verify concordance calculation between v1 and v2 responses."""
        from scripts.audit_v1_vs_v2_extractions import calculate_metrics

        v1_records = [
            {"q_id": "BC_Q1", "predicted_val": 1.0, "confidence": 0.9, "citation": "Quote A"},
            {"q_id": "BC_Q2", "predicted_val": 0.5, "confidence": 0.8, "citation": "Quote B"},
            {"q_id": "BC_Q3", "predicted_val": 0.0, "confidence": 0.7, "citation": None},
            {"q_id": "BC_Q4", "predicted_val": 0.75, "confidence": 0.85, "citation": "Quote C"},
        ]

        v2_records = [
            {"q_id": "BC_Q1", "predicted_val": 1.0, "confidence": 0.95, "citation": "Quote A", "page_number": 1},
            {"q_id": "BC_Q2", "predicted_val": 0.5, "confidence": 0.85, "citation": "Quote B", "page_number": 2},
            {"q_id": "BC_Q3", "predicted_val": 0.25, "confidence": 0.75, "citation": None, "page_number": None},
            {"q_id": "BC_Q4", "predicted_val": 0.75, "confidence": 0.9, "citation": "Quote C", "page_number": 3},
        ]

        res = calculate_metrics(v1_records, v2_records)
        self.assertEqual(res["total_compared"], 4)
        self.assertEqual(res["exact_matches"], 3)  # BC_Q1, BC_Q2, BC_Q4 match
        self.assertAlmostEqual(res["concordance_pct"], 75.0)
        self.assertEqual(res["v2_grounded_citations"], 3)
        self.assertAlmostEqual(res["v2_grounding_rate_pct"], 100.0)

    def test_02_multi_startup_aggregation(self):
        """Verify calculate_metrics does not overwrite records when multiple startups share question IDs."""
        from scripts.audit_v1_vs_v2_extractions import calculate_metrics

        v1_records = [
            # Startup A
            {"startup_id": "startup_A", "q_id": "BC_Q1", "predicted_val": 1.0, "confidence": 0.9, "citation": "Quote A1"},
            {"startup_id": "startup_A", "q_id": "BC_Q2", "predicted_val": 0.5, "confidence": 0.8, "citation": "Quote A2"},
            # Startup B (same question IDs)
            {"startup_id": "startup_B", "q_id": "BC_Q1", "predicted_val": 0.0, "confidence": 0.9, "citation": "Quote B1"},
            {"startup_id": "startup_B", "q_id": "BC_Q2", "predicted_val": 0.5, "confidence": 0.8, "citation": "Quote B2"},
        ]

        v2_records = [
            # Startup A
            {"startup_id": "startup_A", "q_id": "BC_Q1", "predicted_val": 1.0, "confidence": 0.95, "citation": "Quote A1", "page_number": 1},
            {"startup_id": "startup_A", "q_id": "BC_Q2", "predicted_val": 0.5, "confidence": 0.85, "citation": "Quote A2", "page_number": 2},
            # Startup B
            {"startup_id": "startup_B", "q_id": "BC_Q1", "predicted_val": 1.0, "confidence": 0.9, "citation": "Quote B1", "page_number": 1},  # mismatch vs v1 (0.0 vs 1.0)
            {"startup_id": "startup_B", "q_id": "BC_Q2", "predicted_val": 0.5, "confidence": 0.85, "citation": "Quote B2", "page_number": 3},
        ]

        res = calculate_metrics(v1_records, v2_records)
        # Total compared must be 4 (2 questions * 2 startups), NOT 2!
        self.assertEqual(res["total_compared"], 4, "Must compare all questions across all startups without key collisions")
        self.assertEqual(res["exact_matches"], 3)  # A:Q1, A:Q2, B:Q2 match; B:Q1 differs
        self.assertAlmostEqual(res["concordance_pct"], 75.0)
        self.assertEqual(res["v2_grounded_citations"], 4)
        self.assertAlmostEqual(res["v2_grounding_rate_pct"], 100.0)
        self.assertEqual(res["by_category"]["BC"]["questions"], 4)


if __name__ == "__main__":
    unittest.main()

