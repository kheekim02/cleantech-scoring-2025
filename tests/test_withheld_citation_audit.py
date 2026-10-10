"""Classifier checks for the short withheld-citation audit."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_audit():
    path = ROOT / "scripts" / "audit_withheld_citations.py"
    spec = importlib.util.spec_from_file_location("audit_withheld", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestWithheldCitationAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_audit()

    def test_classifies_fabricated_paraphrase_splice_and_wrong_doc(self):
        primary = [{
            "chunk_id": "p1",
            "source_pdf": "bmc.pdf",
            "doc_type": "EBD1",
            "page_no": 1,
            "text": "We sell graphite anodes made from recycled plastic to battery makers.",
        }]
        other = [{
            "chunk_id": "o1",
            "source_pdf": "pitch.pdf",
            "doc_type": "EBD8",
            "page_no": 2,
            "text": "Enhance the resilience of the graphite supply chain for BattCos.",
        }]
        chunks = primary + other

        fabricated = self.mod.classify_citation(
            "Enhance the resilience of the graphite supply chain for BattCos",
            0.75,
            chunks,
            primary,
        )
        self.assertEqual(fabricated["class"], "wrong_document")

        paraphrase = self.mod.classify_citation(
            "We sell graphite anodes produced from recycled plastics for battery manufacturers",
            1.0,
            chunks,
            primary,
        )
        self.assertIn(paraphrase["class"], {"paraphrase_or_edit", "weak_paraphrase"})

        splice = self.mod.classify_citation(
            "We sell graphite anodes made from recycled plastic to battery makers. "
            "Enhance the resilience of the graphite supply chain for BattCos.",
            1.0,
            chunks,
            primary,
        )
        self.assertEqual(splice["class"], "splice")

        exact = self.mod.classify_citation(
            "We sell graphite anodes made from recycled plastic to battery makers.",
            1.0,
            chunks,
            primary,
        )
        self.assertEqual(exact["class"], "would_pass")

        empty = self.mod.classify_citation(None, 1.0, chunks, primary)
        self.assertEqual(empty["class"], "empty_citation")


if __name__ == "__main__":
    unittest.main()
