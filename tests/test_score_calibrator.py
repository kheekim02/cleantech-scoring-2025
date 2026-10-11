# tests/test_score_calibrator.py
import unittest
from src.scorer.score_calibrator import calibrate_record


class TestScoreCalibrator(unittest.TestCase):
    def test_subjective_fractional_mapping(self):
        # A question with fractional tiers [0.0, 0.25, 0.5, 0.75, 1.0]
        q_def = {
            "q_id": "BC_Q1",
            "cat_code": "BC",
            "options": [{"val": 0.0}, {"val": 0.25}, {"val": 0.5}, {"val": 0.75}, {"val": 1.0}],
        }
        # Medium evidence with 0.65 confidence should map to fractional 0.5 rather than collapsing to 0.0
        rec = {
            "q_id": "BC_Q1",
            "predicted_val": 0.0,
            "confidence": 0.65,
            "citation": "Customer segments include municipal transit authorities.",
            "rationale": "Applicant explicitly mentions municipal transit authorities as primary target customer segment.",
        }
        cal = calibrate_record(rec, q_def)
        self.assertGreater(cal["predicted_val"], 0.0)
        self.assertIn(cal["predicted_val"], [0.25, 0.5, 0.75])
        self.assertTrue(cal.get("calibrated", False))

    def test_strict_preservation_when_no_citation(self):
        q_def = {
            "q_id": "BC_Q1",
            "cat_code": "BC",
            "options": [{"val": 0.0}, {"val": 1.0}],
        }
        # If no citation and 0.0, never calibrate upward (anti-hallucination invariant)
        rec = {
            "q_id": "BC_Q1",
            "predicted_val": 0.0,
            "confidence": 0.9,
            "citation": None,
            "rationale": "No evidence found.",
        }
        cal = calibrate_record(rec, q_def)
        self.assertEqual(cal["predicted_val"], 0.0)
        self.assertFalse(cal.get("calibrated", False))


    def test_strict_preservation_when_absence_in_rationale(self):
        q_def = {
            "q_id": "BC_Q1",
            "cat_code": "BC",
            "options": [{"val": 0.0}, {"val": 0.25}, {"val": 0.5}, {"val": 0.75}, {"val": 1.0}],
        }
        rec = {
            "q_id": "BC_Q1",
            "predicted_val": 0.0,
            "confidence": 0.8,
            "citation": "Transit authority contact listed.",
            "rationale": "Document does not provide customer segment validation.",
        }
        cal = calibrate_record(rec, q_def)
        self.assertEqual(cal["predicted_val"], 0.0)
        self.assertFalse(cal.get("calibrated", False))

    def test_strict_preservation_when_negative_citation(self):
        q_def = {
            "q_id": "BC_Q1",
            "cat_code": "BC",
            "options": [{"val": 0.0}, {"val": 0.5}, {"val": 1.0}],
        }
        rec = {
            "q_id": "BC_Q1",
            "predicted_val": 0.0,
            "confidence": 0.7,
            "citation": "not mentioned in the text",
            "rationale": "Applicant mentions nothing about revenue.",
        }
        cal = calibrate_record(rec, q_def)
        self.assertEqual(cal["predicted_val"], 0.0)
        self.assertFalse(cal.get("calibrated", False))


if __name__ == "__main__":
    unittest.main()
