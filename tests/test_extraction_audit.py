"""Chunk and score audits for a v4 extraction."""
import importlib.util
import unittest
from pathlib import Path

from scripts.audit_v4_extraction import (
    CAT_PRIMARY_SOURCES,
    audit_chunks,
    audit_records,
)

ROOT = Path(__file__).resolve().parents[1]


def load_extractor():
    path = ROOT / "scripts" / "14_ai_copilot_extractor_v2.py"
    spec = importlib.util.spec_from_file_location("extractor_v2_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def chunk(filename, doc_type, text, page=1):
    return {
        "chunk_id": f"{filename}_{page}",
        "source_pdf": filename,
        "doc_type": doc_type,
        "page_no": page,
        "text": text,
        "type": "text",
    }


IMPACT = (
    "We protect the environment by upcycling waste plastic into high-performance "
    "graphite battery anode materials. We are committed to providing good clean jobs "
    "in our cities."
)


class TestExtractionAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor = load_extractor()

    def test_primary_map_matches_the_extractor(self):
        self.assertEqual(CAT_PRIMARY_SOURCES, self.extractor.CAT_PRIMARY_SOURCES)

    def test_grounded_score_passes(self):
        chunks = [chunk("06_ImpactStatement.pdf", "EBD2", IMPACT)]
        record = {
            "q_id": "ES_Q1",
            "predicted_val": 1.0,
            "confidence": 0.95,
            "citation": IMPACT,
            "rationale": "The statement describes waste upcycling and clean jobs.",
        }
        rubric = [{
            "new_q_id": "ES_Q1",
            "cat_code": "ES",
            "text": "Describe the environmental benefit.",
            "options": [{"val": 0}, {"val": 0.5}, {"val": 1}],
        }]
        self.assertEqual(audit_records([record], chunks, rubric), [])

    def test_citation_from_the_wrong_document_fails(self):
        chunks = [
            chunk("16_Executive_Summary.pdf", "EBD6", IMPACT),
            chunk("06_EBD2ImpactStatement.pdf", "EBD2", "Impact statement placeholder."),
        ]
        record = {
            "q_id": "ES_Q1",
            "predicted_val": 1.0,
            "confidence": 0.9,
            "citation": IMPACT,
            "rationale": "Quoted from the packet.",
        }
        findings = audit_records([record], chunks)
        self.assertTrue(any(item["check"] == "citation_not_primary" for item in findings))

    def test_a_name_that_also_appears_in_another_file_stays_primary(self):
        chunks = [
            chunk("02_Team_Targets.pdf", "M8", "CarbonDots is hiring advisors."),
            chunk("16_Executive_Summary.pdf", "EBD6", "The applicant name is CarbonDots."),
        ]
        record = {
            "q_id": "IS_Q1",
            "predicted_val": 1.0,
            "confidence": 1.0,
            "citation": "CarbonDots",
            "rationale": "The executive summary states the company name.",
        }
        rubric = [{
            "new_q_id": "IS_Q1",
            "cat_code": "IS",
            "text": "Does the company have a formal company name?",
            "options": [{"val": 0}, {"val": 1}],
        }]
        self.assertEqual(audit_records([record], chunks, rubric), [])

    def test_template_citation_fails(self):
        text = "Essential Business Deliverable #2: write your impact statement here for the judges."
        chunks = [chunk("06_EBD2ImpactStatement.pdf", "EBD2", text)]
        record = {
            "q_id": "ES_Q1",
            "predicted_val": 1.0,
            "confidence": 0.4,
            "citation": text,
            "rationale": "The template line was quoted.",
        }
        findings = audit_records([record], chunks)
        self.assertTrue(any(item["check"] == "citation_template" for item in findings))

    def test_rationale_sdg_numbers_must_be_in_the_primary_text(self):
        chunks = [chunk("06_EBD2ImpactStatement.pdf", "EBD2", IMPACT)]
        record = {
            "q_id": "ES_Q1",
            "predicted_val": 1.0,
            "confidence": 0.95,
            "citation": IMPACT,
            "rationale": "This aligns with SDG 12, SDG 8, and SDG 13.",
        }
        rubric = [{
            "new_q_id": "ES_Q1",
            "cat_code": "ES",
            "text": "Company purpose addresses two or more United Nations Sustainable Development Goals (SDGs).",
            "options": [{"val": 0}, {"val": 0.5}, {"val": 1}],
        }]
        checks = {item["check"] for item in audit_records([record], chunks, rubric)}
        self.assertIn("rationale_unsupported", checks)
        self.assertIn("score_without_sdg", checks)

    def test_chunk_template_line_and_page_are_checked(self):
        chunks = [
            chunk("06_EBD2ImpactStatement.pdf", "EBD2", "Key Deliverable: Essential Business Deliverable #2."),
            {"source_pdf": "07_notes.pdf", "doc_type": "OTHER", "page_no": 0, "text": "A note."},
        ]
        checks = {item["check"] for item in audit_chunks(chunks)}
        self.assertIn("chunk_template", checks)
        self.assertIn("chunk_page", checks)

    def test_exact_primary_span_is_kept_and_a_splice_is_withheld(self):
        question = {
            "new_q_id": "ES_Q9",
            "cat_code": "ES",
            "text": "Describe the environmental benefit.",
            "options": [{"val": 0}, {"val": 1}],
        }
        kept = self.extractor.accept_model_answer(
            {
                "predicted_val": 1.0,
                "confidence": 0.9,
                "citation": IMPACT,
                "rationale": "The statement describes waste upcycling and clean jobs.",
            },
            IMPACT,
            question,
        )
        self.assertEqual(kept["predicted_val"], 1.0)
        self.assertEqual(kept["citation"], IMPACT)
        self.assertIsNone(kept["source_pdf"])
        self.assertIsNone(kept["page_number"])

        spliced = (
            "We protect the environment by upcycling waste plastic into high-performance "
            "graphite battery anode materials. The pitch restates the same impact in different words."
        )
        withheld = self.extractor.accept_model_answer(
            {
                "predicted_val": 1.0,
                "confidence": 0.9,
                "citation": spliced,
                "rationale": "Both documents describe the impact.",
            },
            IMPACT,
            question,
        )
        self.assertIsNone(withheld["predicted_val"])
        self.assertIsNone(withheld["citation"])
        self.assertEqual(withheld["confidence"], 0.0)

    def test_unsupported_sdg_number_nulls_the_score(self):
        question = {
            "new_q_id": "ES_Q1",
            "cat_code": "ES",
            "text": "Company purpose addresses two or more United Nations Sustainable Development Goals (SDGs).",
            "options": [{"val": 0}, {"val": 0.5}, {"val": 1}],
        }
        kept = self.extractor.accept_model_answer(
            {
                "predicted_val": 1.0,
                "confidence": 0.95,
                "citation": IMPACT,
                "rationale": "This aligns with SDG 12, SDG 8, and SDG 13.",
            },
            IMPACT,
            question,
        )
        self.assertEqual(kept["predicted_val"], 0.0)
        self.assertEqual(kept["citation"], IMPACT)
        self.assertNotIn("SDG", kept["rationale"])
        from scripts.audit_v5_parsed import audit_parsed_records
        self.assertEqual(audit_parsed_records([kept], {"ES": IMPACT}, [question]), [])
