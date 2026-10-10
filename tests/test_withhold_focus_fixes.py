"""Regression tests for parsed-markdown withhold focus fixes."""
import unittest

from src.scorer.schemas import (
    densify_markdown_for_match,
    is_negative_citation,
    match_citation_to_text,
    QuestionEvaluation,
)


class TestWithholdFocusFixes(unittest.TestCase):
    def test_densify_joins_short_canvas_lines(self):
        raw = (
            "Enhance the resilience of\n"
            "the graphite supply chain\n"
            "for BattCos, long-term\n"
            "stability\n"
        )
        dense = densify_markdown_for_match(raw)
        self.assertIn(
            "Enhance the resilience of the graphite supply chain for BattCos, long-term stability",
            dense.replace("\n", " "),
        )
        quote = "Enhance the resilience of the graphite supply chain for BattCos, long-term stability"
        self.assertTrue(match_citation_to_text(quote, raw))

    def test_market_gap_there_is_no_is_not_a_negative_citation(self):
        quote = (
            "Operators are flaring significant volumes of gas and missing out because "
            "there is no simple, SCADA-integrated way to track credits."
        )
        self.assertFalse(is_negative_citation(quote))
        body = quote + "\nOther notes about the product."
        self.assertTrue(match_citation_to_text(quote, body))

    def test_evaluator_absence_language_is_still_rejected(self):
        self.assertTrue(is_negative_citation("The provided text does not mention trademarks."))
        self.assertTrue(is_negative_citation("There is no mention of open-source code."))

    def test_short_exact_citations_are_kept(self):
        self.assertEqual(
            QuestionEvaluation(q_id="IS_Q1", predicted_val=1.0, citation="SPCTA").citation,
            "SPCTA",
        )
        self.assertEqual(
            QuestionEvaluation(q_id="L_Q37", predicted_val=1.0, citation="None.").citation,
            "None.",
        )
        self.assertTrue(match_citation_to_text("SPCTA", "Company: SPCTA\nPhoenix, AZ"))
        self.assertTrue(match_citation_to_text("None.", "Environmental permits?\nNone.\nEnd."))


if __name__ == "__main__":
    unittest.main()
