"""Parsed-markdown scoring: continuous primary text, no PDF provenance."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from scripts.audit_v5_parsed import audit_parsed_records
from src.scorer.schemas import match_citation_to_text

ROOT = Path(__file__).resolve().parents[1]


def load_extractor():
    path = ROOT / "scripts" / "14_ai_copilot_extractor_v2.py"
    spec = importlib.util.spec_from_file_location("extractor_v5_parsed", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BMC = (
    "Value Propositions\n"
    "Enhance the resilience of\n"
    "the graphite supply chain\n"
    "for BattCos, long-term\n"
    "stability\n"
)

IMPACT = (
    "We protect the environment by upcycling waste plastic into high-performance "
    "graphite battery anode materials."
)


class TestParsedMarkdownScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_extractor()

    def test_defaults_point_at_v5_parsed_cache(self):
        self.assertTrue(self.mod.SHADOW_CACHE_NAME.endswith("ai_cache_v5_parsed"))
        self.assertTrue(self.mod.default_cache_dir().endswith("ai_cache_v5_parsed"))
        self.assertTrue(str(self.mod.DEFAULT_PARSED_DIR).endswith("parsed_clean_v4") or "parsed_clean_v4" in str(self.mod.DEFAULT_PARSED_DIR))

    def test_markdown_context_is_primary_only_and_continuous(self):
        docs = [
            {"source_pdf": "pitch.pdf", "doc_type": "EBD8", "text": "PITCH " * 40},
            {"source_pdf": "bmc.pdf", "doc_type": "EBD1", "text": BMC},
            {"source_pdf": "exec.pdf", "doc_type": "EBD6", "text": "EXEC NAME"},
        ]
        bc = self.mod.build_category_context_from_docs(docs, "BC", char_limit=5000)
        self.assertTrue(bc["has_primary"])
        self.assertEqual(bc["primary_filenames"], ["bmc.pdf"])
        self.assertIn("Enhance the resilience of", bc["text"])
        self.assertIn("for BattCos, long-term", bc["text"])
        self.assertNotIn("PITCH", bc["text"])
        self.assertNotIn("[Role: SECONDARY]", bc["text"])
        self.assertIn("Enhance the resilience of", bc["primary_text"])

    def test_cross_line_bmc_quote_matches_joined_markdown(self):
        quote = "Enhance the resilience of the graphite supply chain for BattCos, long-term stability"
        self.assertTrue(match_citation_to_text(quote, BMC))
        kept = self.mod.accept_model_answer(
            {
                "predicted_val": 0.75,
                "confidence": 0.9,
                "citation": quote,
                "rationale": "The canvas states supply-chain resilience for BattCos.",
            },
            BMC,
            {
                "new_q_id": "BC_Q1",
                "cat_code": "BC",
                "text": "How clearly is the value proposition understood?",
                "options": [{"val": 1.0}, {"val": 0.75}, {"val": 0.5}, {"val": 0.25}, {"val": 0.0}],
            },
        )
        self.assertEqual(kept["predicted_val"], 0.75)
        self.assertEqual(kept["citation"], quote)
        self.assertIsNone(kept["source_pdf"])
        self.assertIsNone(kept["page_number"])

    def test_zero_score_without_citation_is_kept(self):
        kept = self.mod.accept_model_answer(
            {
                "predicted_val": 0.0,
                "confidence": 0.95,
                "citation": None,
                "rationale": "The canvas lists segments but no customer interviews.",
            },
            BMC,
            {
                "new_q_id": "BC_Q3",
                "cat_code": "BC",
                "text": "How many customers were interviewed?",
                "options": [{"val": 0}, {"val": 1}],
            },
        )
        self.assertEqual(kept["predicted_val"], 0.0)
        self.assertIsNone(kept["citation"])
        self.assertEqual(
            audit_parsed_records(
                [kept],
                {"BC": BMC},
                [{"new_q_id": "BC_Q3", "cat_code": "BC", "text": "interviews", "options": [{"val": 0}, {"val": 1}]}],
            ),
            [],
        )

    def test_sdg_invention_is_withheld(self):
        withheld = self.mod.accept_model_answer(
            {
                "predicted_val": 1.0,
                "confidence": 0.9,
                "citation": IMPACT,
                "rationale": "This addresses SDG 12 and SDG 8.",
            },
            IMPACT,
            {
                "new_q_id": "ES_Q1",
                "cat_code": "ES",
                "text": "Company purpose addresses two or more United Nations Sustainable Development Goals (SDGs).",
                "options": [{"val": 0}, {"val": 0.5}, {"val": 1}],
            },
        )
        # Grounded quote is kept; SDG-only invention downgrades to 0 with a clean rationale.
        self.assertEqual(withheld["predicted_val"], 0.0)
        self.assertEqual(withheld["citation"], IMPACT)
        self.assertNotIn("SDG", withheld["rationale"] or "")
        self.assertEqual(
            audit_parsed_records(
                [withheld],
                {"ES": IMPACT},
                [{
                    "new_q_id": "ES_Q1",
                    "cat_code": "ES",
                    "text": "Company purpose addresses two or more United Nations Sustainable Development Goals (SDGs).",
                    "options": [{"val": 0}, {"val": 0.5}, {"val": 1}],
                }],
            ),
            [],
        )

    def test_load_parsed_documents_classifies_bmc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "03_Team_BMC.pdf.md"
            path.write_text(BMC, encoding="utf-8")
            docs = self.mod.load_parsed_documents(root)
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0]["source_pdf"], "03_Team_BMC.pdf")
            self.assertEqual(docs[0]["doc_type"], "EBD1")


if __name__ == "__main__":
    unittest.main()
