"""Map real founder PDFs onto the scorer's category dropdown.

Each case reads the extracted markdown, not just the filename. The phrases are
words that appear in that file, so a rename-only classifier cannot pass.
"""
import importlib.util
import json
import random
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSED = ROOT / "data" / "parsed_clean"
RENDER_JS = ROOT / "site" / "js" / "render.js"


def load_extractor():
    path = ROOT / "scripts" / "14_ai_copilot_extractor_v2.py"
    spec = importlib.util.spec_from_file_location("extractor_v2_interface", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pdf_markdown(company, filename):
    path = PARSED / company / "converted" / f"{filename}.md"
    if not path.is_file():
        raise AssertionError(f"missing extracted text: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def assert_phrases(text, required, forbidden=()):
    folded = text.lower()
    for phrase in required:
        if phrase.lower() not in folded:
            snippet = " ".join(text.split())[:240]
            raise AssertionError(f"text missing {phrase!r}. Opening: {snippet}")
    for phrase in forbidden:
        if phrase.lower() in folded:
            raise AssertionError(f"text unexpectedly contains {phrase!r}")


class TestInterfaceDocMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PARSED.is_dir():
            raise unittest.SkipTest("data/parsed_clean is not present")
        cls.mod = load_extractor()
        from scripts.docling_ingestion import detect_doc_type
        cls.detect = staticmethod(detect_doc_type)

    def test_dropdown_labels_match_render_js(self):
        source = RENDER_JS.read_text(encoding="utf-8")
        block = re.search(r"categoryNames:\s*\{([^}]+)\}", source)
        self.assertIsNotNone(block)
        found = dict(re.findall(r"'([A-Z]+)'\s*:\s*'([^']+)'", block.group(1)))
        self.assertEqual(found, self.mod.INTERFACE_CATEGORY_LABELS)

    def test_each_deliverable_is_primary_for_one_category(self):
        owners = {}
        for cat, types in self.mod.CAT_PRIMARY_SOURCES.items():
            for doc_type in types:
                self.assertNotIn(doc_type, owners, f"{doc_type} owned by {owners.get(doc_type)} and {cat}")
                owners[doc_type] = cat
        self.assertEqual(self.mod.interface_categories_for_doc_type("OTHER"), [])
        self.assertEqual(self.mod.interface_categories_for_doc_type("EBD2"), ["ES"])
        self.assertEqual(self.mod.interface_categories_for_doc_type("EBD6"), ["IS"])

    def test_seeded_company_packet_matches_its_text(self):
        """Random(2026) over the allowlist companies that have parsed text."""
        allow = json.loads((ROOT / "data" / "active_startup_allowlist.json").read_text())
        present = [
            row["startup_id"]
            for row in allow["startups"]
            if (PARSED / row["startup_id"] / "converted").is_dir()
        ]
        company = random.Random(2026).choice(sorted(present))
        self.assertEqual(company, "CarbonDots")

        # filename, doc type, interface category or None, phrases that are in the file
        packet = [
            ("01_Polypropylene_Turned_into_Luminescent_Carbon_Dots_-_ChemistryViews.pdf", "OTHER", None,
             ["Polypropylene", "ChemistryViews"], ["Team Target", "Business Model Canvas"]),
            ("02_CarbonDots-2025_Team_Targets.pdf", "M8", "T",
             ["Team Targets", "Bruce Willner"], []),
            ("03_CarbonDots-BMC-8June.pdf", "EBD1", "BC",
             ["Waste management", "Battery manufacturers"], []),
            ("04_CarbonDots_M2ImpactSustainaiblityQuestions.pdf", "M2", "ES",
             ["Impact/Sustainability Questions"], []),
            ("05_CarbonDots_GHGWorkbook.pdf", "M2", "ES",
             ["Greenhouse Gas Emission Reduction Potential"], ["Year Founded"]),
            ("06_CarbonDots_EBD2ImpactStatement.pdf", "EBD2", "ES",
             ["Impact Statement", "waste plastic"], []),
            ("07_CarbonDots_M3AssignmentQuestion.pdf", "M3", "PMF",
             ["Product/Market Fit", "Customer Discovery"], []),
            ("08_CarbonDots_M4_Questions.pdf", "M4", "M",
             ["Markets and Getting to Them"], []),
            ("09_CarbonDots_EBD3CustomerSegmentationCompetitiveMatrix.pdf", "EBD3", "M",
             ["Customer Segmentation"], []),
            ("10_CarbonDots_EBD4TechnologyValidation.pdf", "EBD4", "TP",
             ["TRL", "Material made in the lab"], []),
            ("11_CarbonDots_M6Questions.pdf", "M6", "F",
             ["Finances and Funding"], []),
            ("12_CarbonDots_2025FinancialProjection.pdf", "EBD5", "F",
             ["Financial Projection", "Total Income"], []),
            ("13_CarbonDots_M7Questions.pdf", "M7", "L",
             ["Legal Questions"], []),
            ("14_CarbonDots_M8Questions.pdf", "M8", "T",
             ["Management Team"], []),
            ("15_CarbonDots_InclusionAssignment.pdf", "OTHER", None,
             ["Inclusion Assignment", "Inclusive Design"], ["Team Target #1"]),
            ("16_CarbonDots_2025_Cleantech_Open_One_Page_Executive_Summary.pdf", "EBD6", "IS",
             ["Bruce Willner", "Year Founded"], []),
            ("17_CarbonDots_CTO_PitchDeck.pdf", "EBD8", "IP",
             ["Graphite Demand Is Soaring"], []),
        ]
        for filename, doc_type, cat, required, forbidden in packet:
            with self.subTest(filename=filename):
                self.assertEqual(self.detect(filename), doc_type)
                cats = self.mod.interface_categories_for_doc_type(doc_type)
                if cat is None:
                    self.assertEqual(cats, [])
                else:
                    self.assertEqual(cats, [cat])
                    self.assertEqual(self.mod.INTERFACE_CATEGORY_LABELS[cat], {
                        "BC": "Business Canvas",
                        "ES": "Environmental & Social",
                        "F": "Financials",
                        "IP": "Investor Pitch",
                        "IS": "Impact Strategy",
                        "L": "Legal",
                        "M": "Marketing",
                        "PMF": "Product Market Fit",
                        "T": "Team",
                        "TP": "Tech / Product",
                    }[cat])
                text = pdf_markdown(company, filename)
                assert_phrases(text, required, forbidden)

    def test_filename_collisions_follow_the_text(self):
        cases = [
            # Module 1 in the name, but the body is a nine-block canvas.
            ("LeverageTech_Innovations",
             "03_Business_Model_Canvas_LeverageTech_Innovations_Module_1.pdf",
             "EBD1", "BC",
             ["Customer Segments", "Value Propositions", "Key Partnerships"],
             []),
            # EBD 1 in the name, but the body is team targets.
            ("LeverageTech_Innovations",
             "01_Leveragetech_EBD_1_Team_Targets_CTO_Accelerator_2025.pdf",
             "M8", "T",
             ["Team Target #1", "LeverageTech"],
             ["Customer Segments"]),
            # Heading mentions the canvas; the sheet is interview notes.
            ("LeverageTech_Innovations",
             "02_Leveragetech_M1CustomerDiscoveryInterviews.pdf",
             "M1", "PMF",
             ["Five Customer Interviews", "key insights"],
             []),
            # EBD4 in the name; the body is the Blair Smith customer-archetype exercise.
            ("LeverageTech_Innovations",
             "08_Leveragetech_EBD4_Matrix_and_architype.pdf",
             "M3", "PMF",
             ["Customer Archetype", "Blair Smith"],
             ["Technology Readiness Level"]),
            # Bare EBD6 file is the one-page summary, shown under Impact Strategy.
            ("LeverageTech_Innovations",
             "14_Leveragetech_EBD6.pdf",
             "EBD6", "IS",
             ["Business Description", "Year Founded", "jbuz13@gmail"],
             ["Impact Statement:"]),
            # EBD9 plus the word Executive Summary is still the one-pager, not the GHG workbook.
            ("Aris_Hydronics",
             "16_ArisHydronics_EBD9ExecutiveSummary_docx.pdf",
             "EBD6", "IS",
             ["Business Description", "robert@arishydronics.com"],
             ["Greenhouse Gas Emission Reduction Potential"]),
            # Same EBD9 number on a GHG workbook stays Environmental & Social.
            ("Biospheric_AI",
             "05_Biospheric_AI_EBD9_GHG_ERP_Workbook.pdf",
             "M2", "ES",
             ["Greenhouse Gas Emission Reduction Potential", "NYSP2I"],
             ["Year Founded"]),
            # Template calls technology validation "Deliverable #5"; the body is TRL, not a P&L.
            ("Aris_Hydronics",
             "10_Aris_Hydronics_EBD5TechnologyValidation.pdf",
             "EBD4", "TP",
             ["Product Technology Validation", "TRL 7"],
             ["Total Income"]),
            # EBD10 must not collapse into the canvas. The body is a slide deck.
            ("Aris_Hydronics",
             "17_ArisHydronics_EBD10PitchDeck.pdf",
             "EBD8", "IP",
             ["The Future of Heating", "Heat Pump"],
             ["Key Partnerships"]),
            # Module 10 used to match Module 1. The body is an investor pitch.
            ("We_Think_Global",
             "15_Module_10_CTO_Investor_Pitch_Deck_August_26_2025.pdf",
             "EBD8", "IP",
             ["Investor Pitch", "CIRCRIT"],
             ["Customer Interview Capture Sheet"]),
            # Glued EBD1 plus interview notes is discovery, not the canvas group.
            ("Wind_Pulse_Energy",
             "03_WindPulseEnergy_EBD1CustomerInterviewCaptures.pdf",
             "M1", "PMF",
             ["Customer Interview Capture Sheet", "at least 5 customer interviews"],
             []),
            # Typo "Modle" is still a canvas: partners, cost drivers, value drivers.
            ("Condor_Calibration_Services",
             "05_Condor_Business_Modle_Canvas.pdf",
             "EBD1", "BC",
             ["Cost Drivers", "Value Drivers"],
             []),
            # Body discusses greenhouse gas, but the file is a one-pager, so the dropdown group is Impact Strategy.
            ("Condor_Calibration_Services",
             "02_Condor_one_pager.pdf",
             "EBD6", "IS",
             ["Condor provides", "greenhouse gas"],
             ["Self-Assessment Workbook"]),
            # EBD6 glued to a financial workbook is Financials, not Impact Strategy.
            ("Compocity",
             "14_Compocity_EBD6FinancialPlan_workbook.pdf",
             "EBD5", "F",
             ["Assumptions", "Revenue"],
             ["Year Founded"]),
            # Legal questions with no M7 token.
            ("Fortifyy_PBC",
             "14_Fortifyy_Legal_Questions.pdf",
             "M7", "L",
             ["Legal Questions", "Public Benefit Corporation"],
             []),
            # Module 3 segmentation outranks the module number.
            ("Cryodrives",
             "05_Cryodrives_Module_3_Customer_Segmentation_Competitive_Matrix_and_Market_Ecosystem.pdf",
             "EBD3", "M",
             ["Customer Segmentation", "Fleet Operations Managers"],
             []),
            # Module 4 technology validation outranks the module number.
            ("Cryodrives",
             "06_Cryodrives_Module_4_Product_Technology_Validation.pdf",
             "EBD4", "TP",
             ["Technology Readiness Level", "HD-POW"],
             []),
        ]
        for company, filename, doc_type, cat, required, forbidden in cases:
            with self.subTest(company=company, filename=filename):
                self.assertEqual(self.detect(filename), doc_type)
                self.assertEqual(self.mod.interface_categories_for_doc_type(doc_type), [cat])
                label = self.mod.INTERFACE_CATEGORY_LABELS[cat]
                self.assertIn(label, RENDER_JS.read_text(encoding="utf-8"))
                text = pdf_markdown(company, filename)
                assert_phrases(text, required, forbidden)


if __name__ == "__main__":
    unittest.main()
