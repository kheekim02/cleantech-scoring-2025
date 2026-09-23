"""Unit tests for Grounded Extraction Head and Pydantic Schemas."""
import unittest
from typing import Any


class TestGroundedExtractor(unittest.TestCase):
    def test_01_schema_import_and_validation(self):
        """Verify schemas validate standard 0-1 rubric scores."""
        from src.scorer.schemas import QuestionEvaluation

        valid = QuestionEvaluation(
            q_id="BC_Q1",
            predicted_val=0.75,
            confidence=0.85,
            citation="17 offers a modular power-to-ammonia system.",
            source_pdf="02_17_Inc_-_Biz_Model_Canvas.pdf",
            page_number=2,
            bbox={"l": 72.0, "t": 500.0, "r": 300.0, "b": 450.0}
        )
        self.assertEqual(valid.predicted_val, 0.75)
        self.assertEqual(valid.page_number, 2)

    def test_02_schema_rejects_out_of_bounds_score(self):
        """Verify scores outside 0.0 - 1.0 are rejected."""
        from src.scorer.schemas import QuestionEvaluation
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            QuestionEvaluation(q_id="BC_Q1", predicted_val=2.5)

        with self.assertRaises(ValidationError):
            QuestionEvaluation(q_id="BC_Q1", predicted_val=-0.5)

    def test_03_verbatim_grounding_matcher(self):
        """Verify verbatim matching resolves exact chunk, page, and bbox."""
        from src.scorer.schemas import match_citation_to_chunks

        chunks = [
            {
                "chunk_id": "chunk_01",
                "source_pdf": "04_17Inc_EBD2ImpactStatement.pdf",
                "page_no": 1,
                "bbox": {"l": 100.0, "t": 200.0, "r": 500.0, "b": 250.0},
                "text": "17 offers a scalable intermittent ammonia production solution that reduces GHG emissions by 400Mt.",
            },
            {
                "chunk_id": "chunk_02",
                "source_pdf": "09_17Inc_FinancialProjection.pdf",
                "page_no": 3,
                "bbox": {"l": 50.0, "t": 100.0, "r": 400.0, "b": 150.0},
                "text": "Projected year-3 EBITDA is $4.2M with unit economics yielding $240/ton margin.",
            }
        ]

        # Valid verbatim citation
        matched = match_citation_to_chunks("ammonia production solution that reduces GHG emissions", chunks)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["page_number"], 1)
        self.assertEqual(matched["source_pdf"], "04_17Inc_EBD2ImpactStatement.pdf")
        self.assertEqual(matched["bbox"]["l"], 100.0)

        # Hallucinated citation
        hallucinated = match_citation_to_chunks("This company was founded in 1999 by Elon Musk", chunks)
        self.assertIsNone(hallucinated)

        # Negative statement rejected
        negative = match_citation_to_chunks("The document does not mention any financial projections", chunks)
        self.assertIsNone(negative)

    def test_04_raw_model_extraction_schema(self):
        """Verify Instructor-compatible RawModelExtraction schema validation."""
        from src.scorer.schemas import RawModelExtraction
        from pydantic import ValidationError

        # Valid extraction
        ext = RawModelExtraction(
            q_id="BC_Q1",
            predicted_val=1.0,
            confidence=0.9,
            citation="17 offers a scalable intermittent ammonia production solution.",
            rationale="Clear evidence found."
        )
        self.assertEqual(ext.predicted_val, 1.0)
        self.assertEqual(ext.confidence, 0.9)

        # Rejects score > 1.0
        with self.assertRaises(ValidationError):
            RawModelExtraction(q_id="BC_Q1", predicted_val=1.5)

        # Rejects score < 0.0
        with self.assertRaises(ValidationError):
            RawModelExtraction(q_id="BC_Q1", predicted_val=-0.25)

        # Automatically sanitizes negative citation to None
        neg_ext = RawModelExtraction(
            q_id="BC_Q1",
            predicted_val=0.0,
            confidence=0.8,
            citation="The applicant does not mention any customer discovery.",
            rationale="No proof"
        )
        self.assertIsNone(neg_ext.citation, "Negative statements must be sanitized to None")


if __name__ == "__main__":
    unittest.main()

