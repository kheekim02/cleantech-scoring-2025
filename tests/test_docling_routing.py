# tests/test_docling_routing.py
import unittest
from scripts.docling_ingestion import resolve_doc_type, detect_doc_type


class TestDoclingRouting(unittest.TestCase):
    def test_customer_discovery_irregular_filenames(self):
        cases = [
            ("2DaLoop_Customer_Interviews_Summary.pdf", "M1"),
            ("AmpTrans_CustomerDiscoveryLog.pdf", "M1"),
            ("Biomific_Discovery_Notes_Capture.pdf", "M1"),
            ("Averra_Module_1_Interviews.pdf", "M1"),
            ("Calectra_Customer_Archetype_M3.pdf", "M3"),
            ("Acme_ProductMarketFit_Analysis.pdf", "M3"),
            ("Startup_Archetypes_Persona_Sheet.pdf", "M3"),
        ]
        for filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(resolve_doc_type(filename), expected)

    def test_market_matrix_irregular_filenames(self):
        cases = [
            ("2DaLoop_Competitive_Analysis_Matrix.pdf", "EBD3"),
            ("AmpTrans_Customer_Segments_EBD3.pdf", "EBD3"),
            ("Biomific_Competition_Landscape.pdf", "EBD3"),
            ("Calectra_Markets_and_Getting_To_Them_M4.pdf", "M4"),
            ("Averra_Target_Market_Access_M4.pdf", "M4"),
        ]
        for filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(resolve_doc_type(filename), expected)

    def test_opening_text_inference_for_pmf_and_market(self):
        # Even if filename is generic (e.g. Appendix_Document.pdf)
        m1_text = "Customer Discovery Interview Capture Sheet\nInterviewee: John Doe\nPain point: High cost"
        self.assertEqual(resolve_doc_type("Appendix_Document.pdf", m1_text), "M1")

        m3_text = "Module 3: Product-Market Fit & Customer Archetype Exercise\nPrimary Persona: Facility Manager"
        self.assertEqual(resolve_doc_type("Worksheet_Final.pdf", m3_text), "M3")

        ebd3_text = "Competitive Matrix\nCompetitor A | Competitor B | Our Solution\nFeature Comparison"
        self.assertEqual(resolve_doc_type("Landscape_Analysis.pdf", ebd3_text), "EBD3")


if __name__ == "__main__":
    unittest.main()
