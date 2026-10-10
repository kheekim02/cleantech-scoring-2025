"""Primary-document routing for the v2 extractor."""
import importlib.util
import unittest
from pathlib import Path


def load_extractor():
    path = Path(__file__).resolve().parents[1] / "scripts" / "14_ai_copilot_extractor_v2.py"
    spec = importlib.util.spec_from_file_location("extractor_v2_phase2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCategoryContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_extractor()

    def test_es_and_is_routes_and_primary_first_cap(self):
        self.assertEqual(self.mod.CAT_PRIMARY_SOURCES["ES"], ["EBD2", "M2"])
        self.assertEqual(self.mod.CAT_PRIMARY_SOURCES["IS"], ["EBD6"])

        chunks = [
            {"source_pdf": "pitch.pdf", "doc_type": "EBD8", "page_no": 1, "text": "PITCH " * 50},
            {"source_pdf": "impact.pdf", "doc_type": "EBD2", "page_no": 2, "text": "IMPACT EVIDENCE"},
            {"source_pdf": "impact.pdf", "doc_type": "EBD2", "page_no": 3, "text": "SECOND PAGE " * 20},
            {"source_pdf": "exec.pdf", "doc_type": "EBD6", "page_no": 1, "text": "EXEC NAME AND LOGO"},
        ]
        es = self.mod.build_category_context(chunks, "ES", char_limit=5000)
        header = "=== DOCUMENT: impact.pdf [Type: EBD2] [Role: PRIMARY] ==="
        first = "[Page 2] IMPACT EVIDENCE"
        fits_first = len(header) + 2 + len(first)
        short = self.mod.build_category_context(chunks, "ES", char_limit=fits_first)
        is_ctx = self.mod.build_category_context(chunks, "IS", char_limit=5000)
        self.assertTrue(es["has_primary"])
        self.assertEqual(es["primary_filenames"], ["impact.pdf"])
        self.assertIn("IMPACT EVIDENCE", es["text"])
        self.assertIn("SECOND PAGE", es["text"])
        self.assertNotIn("PITCH", es["text"])
        self.assertNotIn("[Role: SECONDARY]", es["text"])
        self.assertIn("IMPACT EVIDENCE", short["text"])
        self.assertNotIn("SECOND PAGE", short["text"])
        self.assertTrue(short["text"].endswith("IMPACT EVIDENCE"))
        self.assertIn("EXEC NAME", is_ctx["text"])
        self.assertNotIn("PITCH", is_ctx["text"])
        self.assertNotIn("IMPACT", is_ctx["text"])
        self.assertIn("[Role: PRIMARY]", is_ctx["text"])

        empty = self.mod.build_category_context(chunks, "L", char_limit=5000)
        self.assertFalse(empty["has_primary"])
        self.assertEqual(empty["text"], "")

    def test_missing_primary_does_not_call_the_model(self):
        class Boom:
            def __getattr__(self, name):
                raise AssertionError(f"model was called via {name}")

        result = self.mod.query_sglang_question(
            Boom(),
            "unused-model",
            "should not be sent",
            {"new_q_id": "ES_Q1", "cat_code": "ES", "text": "SDGs", "options": []},
            has_primary=False,
        )
        self.assertIsNone(result["predicted_val"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertIsNone(result["citation"])
        self.assertIn("No primary source", result["rationale"])


if __name__ == "__main__":
    unittest.main()
