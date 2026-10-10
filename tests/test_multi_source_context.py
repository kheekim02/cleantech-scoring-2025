# tests/test_multi_source_context.py
import importlib
import unittest

_extractor = importlib.import_module("scripts.14_ai_copilot_extractor_v2")
build_category_context_from_docs = _extractor.build_category_context_from_docs
CAT_PRIMARY_SOURCES = _extractor.CAT_PRIMARY_SOURCES
CAT_FALLBACK_SOURCES = getattr(_extractor, "CAT_FALLBACK_SOURCES", None)


class TestMultiSourceContext(unittest.TestCase):
    def test_cat_fallback_sources_exists(self):
        self.assertIsNotNone(CAT_FALLBACK_SOURCES, "CAT_FALLBACK_SOURCES should be defined")
        self.assertIn("PMF", CAT_FALLBACK_SOURCES)
        self.assertIn("M", CAT_FALLBACK_SOURCES)

    def test_pmf_fallback_to_canvas_and_pitch_when_m1_m3_missing(self):
        docs = [
            {
                "source_pdf": "01_Acme_BMC.pdf",
                "doc_type": "EBD1",
                "text": "Canvas Content\nCustomer Segments: Utility Scale Developers\nValue Prop: 40% cost cut",
                "path": "dummy/path1",
            },
            {
                "source_pdf": "08_Acme_Pitch.pdf",
                "doc_type": "EBD8",
                "text": "Pitch Deck\nSlide 5: Traction - 15 customer discovery interviews conducted with OEMs.",
                "path": "dummy/path2",
            },
        ]
        # No M1 or M3 in docs
        ctx = build_category_context_from_docs(docs, "PMF")
        self.assertTrue(ctx["has_primary"])
        self.assertIn("01_Acme_BMC.pdf", ctx["primary_filenames"])
        self.assertIn("Utility Scale Developers", ctx["text"])
        self.assertIn("15 customer discovery interviews", ctx["text"])
        self.assertTrue(ctx.get("is_fallback", False))

    def test_m_fallback_to_canvas_and_pitch_when_ebd3_m4_missing(self):
        docs = [
            {
                "source_pdf": "01_Acme_BMC.pdf",
                "doc_type": "EBD1",
                "text": "Canvas Content\nChannels: Direct B2B enterprise sales and distributor networks.",
                "path": "dummy/path1",
            },
            {
                "source_pdf": "08_Acme_Pitch.pdf",
                "doc_type": "EBD8",
                "text": "Pitch Deck\nSlide 7: Market Size & Competition - Direct competitors X and Y.",
                "path": "dummy/path2",
            },
        ]
        ctx = build_category_context_from_docs(docs, "M")
        self.assertTrue(ctx["has_primary"])
        self.assertIn("Direct B2B enterprise sales", ctx["text"])
        self.assertTrue(ctx.get("is_fallback", False))


if __name__ == "__main__":
    unittest.main()
