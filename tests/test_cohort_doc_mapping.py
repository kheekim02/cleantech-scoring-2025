"""Every allowlisted company's PDFs use the same mapping rules.

Filename patterns are cohort-wide template names. When a filename is generic
(a scan, an assignment number, a UUID), the opening of the extracted text
supplies the deliverable. Supporting letters, news clips, and technical decks
stay unmapped.
"""
import json
import unittest
from pathlib import Path

from scripts.docling_ingestion import (
    DOC_TYPE_INTERFACE,
    infer_doc_type_from_text,
    resolve_doc_type,
)
from tests.test_interface_doc_mapping import (
    PARSED,
    ROOT,
    assert_phrases,
    load_extractor,
    pdf_markdown,
)


class TestCohortDocMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PARSED.is_dir():
            raise unittest.SkipTest("data/parsed_clean is not present")
        cls.mod = load_extractor()
        allow = json.loads((ROOT / "data" / "active_startup_allowlist.json").read_text())
        cls.company_ids = [row["startup_id"] for row in allow["startups"]]

    def test_interface_groups_match_the_extractor(self):
        for doc_type, cat in DOC_TYPE_INTERFACE.items():
            self.assertEqual(self.mod.interface_categories_for_doc_type(doc_type), [cat])

    def test_every_company_title_agrees_with_its_dropdown(self):
        missing = []
        files = 0
        conflicts = []
        for startup_id in self.company_ids:
            converted = PARSED / startup_id / "converted"
            if not converted.is_dir():
                missing.append(startup_id)
                continue
            for path in sorted(converted.glob("*.pdf.md")):
                files += 1
                text = path.read_text(encoding="utf-8", errors="replace")
                filename = path.name[:-3]
                resolved = resolve_doc_type(filename, text)
                inferred = infer_doc_type_from_text(text)
                if inferred is None:
                    continue
                resolved_group = DOC_TYPE_INTERFACE.get(resolved)
                inferred_group = DOC_TYPE_INTERFACE.get(inferred)
                if resolved_group != inferred_group:
                    conflicts.append(f"{startup_id}/{filename}: file {resolved} text {inferred}")
        self.assertEqual(missing, [])
        self.assertEqual(len(self.company_ids), 92)
        self.assertGreaterEqual(files, 1400)
        self.assertEqual(conflicts, [])

    def test_the_same_rules_map_other_companies(self):
        """Cases drawn from companies other than the CarbonDots seed packet."""
        cases = [
            # Generic scan and assignment names. The opening is the deliverable.
            ("H2O_Now", "04_assignment_2_1.pdf", "EBD2", "ES", ["Impact Statement"]),
            ("H2O_Now", "03_Assignment_2.pdf", "M2", "ES", ["Impact/Sustainability Questions"]),
            ("H2O_Now", "05_cleantech_assignment_3.pdf", "M3", "PMF", ["Product/Market Flt"]),
            ("H2O_Now", "06_Adobe_20Scan_20Jun_2027_2C_202025.pdf", "M4", "M", ["Markets and Getting to Them"]),
            ("H2O_Now", "07_cleantech_assignmenent_4.pdf", "EBD3", "M", ["Customer Segmentation"]),
            ("Modulium", "01_PDFF.pdf", "M1", "PMF", ["Customer Interview Capture Sheet"]),
            ("TiltingSolar", "08_TiltingSolar_4Questions.pdf", "M4", "M", ["Markets and Getting to Them"]),
            ("SSG_Environmental", "03_CTO_NOLA_Customer_Research_Plan.pdf", "EBD3", "M", ["Customer Segmentation"]),
            # Filename says Module 6. The sheet is Module 4.
            ("Sustainable_Chemicals", "13_2025_Module_6_Questions.pdf", "M4", "M", ["Markets and Getting to Them"]),
            # Abbreviated and misspelled names used across the cohort.
            ("GreenSight_Technologies", "18_GreenSightTechnologiesPDeck.pdf", "EBD8", "IP", ["The Problem"]),
            ("Calectra", "16_Calectra_deck.pdf", "EBD8", "IP", ["Industrial Heating"]),
            ("Navia_Energy", "19_Navia_Energy_CTO_Deck.pdf", "EBD8", "IP", ["Navia Energy"]),
            ("PolyGone_Systems", "19_PolyGone_Deck_Cleantech_Open.pdf", "EBD8", "IP", ["Microplastic"]),
            ("Vaanelai", "16_VaanelAI_overview_deck-v3-08262025.pdf", "EBD8", "IP", ["energy costs"]),
            ("Hubbletek", "18_Hubbletek-Carbon-Credits-Made-Simple.pdf", "EBD8", "IP", ["Investor Pitch Deck"]),
            ("Bluesonde_Technologies", "18_Bluesonde_1Pager.pdf", "EBD6", "IS", ["INVESTMENT THESIS"]),
            ("Photometrics_AI", "17_PhotometricsAI_1Pager.pdf", "EBD6", "IS", ["Photometrics"]),
            ("Sustainable_Chemicals", "11_Sust_Chem_PMF_for_CTO.pdf", "M3", "PMF", ["Product Market Fit"]),
            ("Lute_&_Ether", "03_Lute_amp_Ether_TargetGoals_June9_2025.pdf", "M8", "T", ["customer discovery calls"]),
            ("2DaLoop", "01_2DaLoop_Revenue_Projections_-_SBIR.pdf", "EBD5", "F", ["Revenue"]),
            ("CIRQ+", "01_CIRQ_2025_5_yr_EBITDA_Forecast.pdf", "EBD5", "F", ["FINANCIAL FORECAST"]),
            ("Core_Envision", "01_Core_Envision_finincial_proj_summary.pdf", "EBD5", "F", ["Avg Revenue"]),
            ("Fortifyy_PBC", "01_Fortifyy_revenue_cost_model_-_Sheet1.pdf", "EBD5", "F", ["Customers"]),
            ("Lumiaq", "01_Itemized_budget_amp_revenue_projection.pdf", "EBD5", "F", ["Projecting Revenues"]),
            ("HomeWise_AI", "01_HomeWise_REVENUE_FORECAST_xlsx_-_RevenueModelExamples.pdf", "EBD5", "F", ["Revenue Forecast"]),
            # Supporting material is not a primary deliverable.
            ("Wind_Pulse_Energy", "02_Technical_Deck_03-04-25b.pdf", "OTHER", None, ["Technical Deck"]),
            ("Bonhomme_&_Associates", "07_Loco-motion_Revenue_Strategy_Deck.pdf", "OTHER", None, ["Revenue Strategy"]),
            ("CarbonDots", "01_Polypropylene_Turned_into_Luminescent_Carbon_Dots_-_ChemistryViews.pdf", "OTHER", None, ["Polypropylene"]),
            ("CarbonDots", "15_CarbonDots_InclusionAssignment.pdf", "OTHER", None, ["Inclusion Assignment"]),
        ]
        for company, filename, doc_type, cat, required in cases:
            with self.subTest(company=company, filename=filename):
                text = pdf_markdown(company, filename)
                self.assertEqual(resolve_doc_type(filename, text), doc_type)
                self.assertEqual(self.mod.interface_categories_for_doc_type(doc_type), [cat] if cat else [])
                assert_phrases(text, required)


if __name__ == "__main__":
    unittest.main()
