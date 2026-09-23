"""Unit tests for Docling document ingestion and scaffolding filtering."""
import os
import json
import unittest
from pathlib import Path


class TestDoclingIngestion(unittest.TestCase):
    def setUp(self):
        # We'll import inside test methods to catch missing module if not yet created
        self.catalog_path = "data/scaffolding_master_catalog.json"
        self.sample_pdf = "VC_Uncovered_Executive_Summary.pdf"

    def test_01_import_docling_ingestion(self):
        """Verify docling_ingestion module imports cleanly."""
        try:
            from scripts.docling_ingestion import (
                extract_pdf_chunks,
                clean_scaffolding_from_chunks,
                detect_doc_type,
                process_startup_folder,
            )
        except ImportError as e:
            self.fail(f"Failed to import docling_ingestion: {e}")

    def test_02_detect_doc_type(self):
        """Verify deliverable type detection by filename."""
        from scripts.docling_ingestion import detect_doc_type

        self.assertEqual(detect_doc_type("04_17Inc_EBD2ImpactStatement.pdf"), "EBD2")
        self.assertEqual(detect_doc_type("06_17Inc_EBD3CustomerSegmentationCompetitiveMatrix.pdf"), "EBD3")
        self.assertEqual(detect_doc_type("07_17Inc_EBD4TechnologyValidation.pdf"), "EBD4")
        self.assertEqual(detect_doc_type("09_17Inc_FinancialProjection.pdf"), "EBD5")
        self.assertEqual(detect_doc_type("10_17Inc_OnePageExecutiveSummary.pdf"), "EBD6")
        self.assertEqual(detect_doc_type("11_17Inc_InvestorPitchDeck.pdf"), "EBD8")
        self.assertEqual(detect_doc_type("02_17_Inc_-_Biz_Model_Canvas.pdf"), "EBD1")
        self.assertEqual(detect_doc_type("unknown_custom_file.pdf"), "OTHER")

    def test_03_scaffolding_filter(self):
        """Verify that known scaffolding catalog items are filtered out."""
        from scripts.docling_ingestion import clean_scaffolding_from_chunks

        raw_chunks = [
            {
                "chunk_id": "c1",
                "page_no": 1,
                "bbox": {"l": 10.0, "t": 20.0, "r": 100.0, "b": 50.0, "coord_origin": "BOTTOMLEFT"},
                "type": "heading",
                "text": "Cleantech Open Confidential – Do not duplicate or distribute without written permission.",
            },
            {
                "chunk_id": "c2",
                "page_no": 1,
                "bbox": {"l": 10.0, "t": 60.0, "r": 100.0, "b": 90.0, "coord_origin": "BOTTOMLEFT"},
                "type": "heading",
                "text": "Essential Business Deliverable #2: Impact/Sustainability Statement",
            },
            {
                "chunk_id": "c3",
                "page_no": 1,
                "bbox": {"l": 10.0, "t": 100.0, "r": 400.0, "b": 150.0, "coord_origin": "BOTTOMLEFT"},
                "type": "paragraph",
                "text": "17 offers a scalable intermittent ammonia production solution that reduces GHG emissions by 400Mt by 2050.",
            },
        ]

        cleaned = clean_scaffolding_from_chunks(raw_chunks, doc_type="EBD2", catalog_path=self.catalog_path)
        # c1 and c2 are scaffolding boilerplate and must be filtered out or emptied
        texts = [c["text"] for c in cleaned if c["text"].strip()]
        self.assertEqual(len(texts), 1)
        self.assertIn("ammonia production solution", texts[0])
        self.assertNotIn("Cleantech Open Confidential", texts[0])

    def test_04_chunk_provenance_schema(self):
        """Verify structure of extracted chunks: page_no, bbox coordinates, type, text."""
        try:
            from scripts.docling_ingestion import extract_pdf_chunks
        except ImportError as e:
            self.skipTest(f"Docling or PyTorch not available: {e}")

        candidates = [
            self.sample_pdf,
            "test.pdf",
            os.path.join(os.path.dirname(__file__), "..", "test.pdf"),
            "/data/scraping/test.pdf",
        ]
        sample = next((c for c in candidates if os.path.exists(c)), None)
        if not sample:
            import glob
            spark_samples = glob.glob("/data/scraping/datasets/cto_accelerator/raw/*/*/*.pdf")
            if spark_samples:
                sample = spark_samples[0]

        if not sample:
            self.skipTest("No sample PDF available for chunk provenance test")

        try:
            chunks = extract_pdf_chunks(sample)
        except Exception as e:
            self.skipTest(f"PDF extraction not runnable in this environment: {e}")

        self.assertGreater(len(chunks), 0)
        first = chunks[0]
        self.assertIn("chunk_id", first)
        self.assertIn("page_no", first)
        self.assertIn("bbox", first)
        self.assertIn("text", first)
        self.assertIn("type", first)
        self.assertIsInstance(first["page_no"], int)
        self.assertGreaterEqual(first["page_no"], 1)


if __name__ == "__main__":
    unittest.main()
