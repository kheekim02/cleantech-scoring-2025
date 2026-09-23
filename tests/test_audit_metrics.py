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
            {"q_id": "BC_Q1", "predicted_val": 1.0, "confidence": 0.95, "citation": "Quote A", "page_number": 1, "bbox": {"l": 10}},
            {"q_id": "BC_Q2", "predicted_val": 0.5, "confidence": 0.85, "citation": "Quote B", "page_number": 2, "bbox": {"l": 20}},
            {"q_id": "BC_Q3", "predicted_val": 0.25, "confidence": 0.75, "citation": None, "page_number": None, "bbox": None},
            {"q_id": "BC_Q4", "predicted_val": 0.75, "confidence": 0.9, "citation": "Quote C", "page_number": 3, "bbox": {"l": 30}},
        ]

        res = calculate_metrics(v1_records, v2_records)
        self.assertEqual(res["total_compared"], 4)
        self.assertEqual(res["exact_matches"], 3)  # BC_Q1, BC_Q2, BC_Q4 match
        self.assertAlmostEqual(res["concordance_pct"], 75.0)
        self.assertEqual(res["v2_grounded_citations"], 3)
        self.assertAlmostEqual(res["v2_grounding_rate_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
