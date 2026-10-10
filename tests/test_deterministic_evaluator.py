# tests/test_deterministic_evaluator.py
import unittest
from src.scorer.deterministic_evaluator import (
    DETERMINISTIC_RULES,
    evaluate_deterministic_criterion,
    find_deterministic_evidence,
)


class TestDeterministicEvaluator(unittest.TestCase):
    def test_f_q1_line_bounded_match(self):
        text = "Year 1 revenue: $100K | Year 2 revenue: $500K | Year 3 revenue: $2M\nRisks"
        val, overridden, reason = evaluate_deterministic_criterion("F_Q1", text, 0.0)
        self.assertTrue(overridden)
        self.assertEqual(val, 1.0)
        self.assertIn("3-Year financial projection model detected", reason)

    def test_f_q1_ignores_year_mentions_scattered_across_document(self):
        text = "Year 1 we hired an engineer.\n" + ("filler line\n" * 200) + "Year 2 pilot.\nYear 3 plan."
        val, overridden, _ = evaluate_deterministic_criterion("F_Q1", text, 0.0)
        self.assertFalse(overridden)
        self.assertEqual(val, 0.0)

    def test_f_q7_breakeven(self):
        text = "Financial Summary\nWe reach breakeven in Year 3 with $150K net profit.\nAppendix"
        val, overridden, _ = evaluate_deterministic_criterion("F_Q7", text, 0.0)
        self.assertTrue(overridden)
        self.assertEqual(val, 1.0)

    def test_l_q1_corp_entity(self):
        text = "Legal Formation\nCompany was incorporated in Delaware as a Delaware C-Corp in 2024."
        val, overridden, _ = evaluate_deterministic_criterion("L_Q1", text, 0.0)
        self.assertTrue(overridden)
        self.assertEqual(val, 1.0)

    def test_l_q14_patent(self):
        text = "Intellectual Property\nPatent No. US 11456789 was granted on clean hydrogen synthesis."
        val, overridden, _ = evaluate_deterministic_criterion("L_Q14", text, 0.0)
        self.assertTrue(overridden)
        self.assertEqual(val, 1.0)

    def test_find_evidence_returns_verbatim_source_line(self):
        text = "Overview\nWe reach breakeven in Year 3 with $150K net profit.\nRisks"
        span = find_deterministic_evidence("F_Q7", text)
        self.assertEqual(span, "We reach breakeven in Year 3 with $150K net profit.")
        self.assertIn(span, text)

    def test_find_evidence_none_for_unruled_question(self):
        self.assertIsNone(find_deterministic_evidence("BC_Q1", "anything"))

    def test_find_evidence_none_when_no_match(self):
        self.assertIsNone(find_deterministic_evidence("F_Q7", "No breakeven mentioned."))

    def test_unruled_question_not_overridden(self):
        val, overridden, _ = evaluate_deterministic_criterion("BC_Q1", "some text", 0.5)
        self.assertFalse(overridden)
        self.assertEqual(val, 0.5)


if __name__ == "__main__":
    unittest.main()
