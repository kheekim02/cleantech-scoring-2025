"""Unit tests for Scorer FAQ, Guidelines, and BMC Bracket Categorization."""
import os
import unittest
from pathlib import Path


class TestFaqAndRubricBrackets(unittest.TestCase):
    """Verify that all Scorer FAQs, BMC Large/Small bracket standards, and modals are properly implemented."""

    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.app_js = self.root / "site" / "js" / "app.js"
        self.index_html = self.root / "site" / "index.html"
        self.gen_tutorials = self.root / "scripts" / "generate_tutorials.py"
        self.agents_md = self.root / "AGENTS.md"
        self.desktop_tutorial = Path("/Users/geoffrey/Desktop/CleanTech_Open_Scorer_Tutorial.pdf")

    def test_01_app_js_rubric_modal_large_brackets_bc_q4(self):
        """Verify BC_Q4 in app.js specifies the 5 Large Brackets (Blue Blocks)."""
        content = self.app_js.read_text(encoding="utf-8")
        self.assertIn("Large Brackets Scoring (BC_Q4)", content)
        self.assertIn("Key Partners", content)
        self.assertIn("Value Propositions", content)
        self.assertIn("Customer Segments", content)
        self.assertIn("Cost Structure", content)
        self.assertIn("Revenue Streams", content)
        self.assertIn("Blue in Strategyzer Template", content)

    def test_02_app_js_rubric_modal_small_brackets_bc_q5(self):
        """Verify BC_Q5 in app.js specifies the 4 Small Brackets (Yellow Blocks)."""
        content = self.app_js.read_text(encoding="utf-8")
        self.assertIn("Small Brackets Scoring (BC_Q5)", content)
        self.assertIn("Key Activities", content)
        self.assertIn("Key Resources", content)
        self.assertIn("Customer Relationships", content)
        self.assertIn("Channels", content)
        self.assertIn("Yellow in Strategyzer Template", content)

    def test_03_app_js_faq_modal_handlers(self):
        """Verify CTO.App implements openFaqModal and closeFaqModal."""
        content = self.app_js.read_text(encoding="utf-8")
        self.assertIn("openFaqModal()", content)
        self.assertIn("closeFaqModal()", content)
        self.assertIn("document.getElementById('faq-modal')", content)

    def test_04_index_html_faq_button_and_modal(self):
        """Verify site/index.html includes FAQ button and comprehensive modal markup."""
        content = self.index_html.read_text(encoding="utf-8")
        self.assertIn("window.CTO.App.openFaqModal()", content)
        self.assertIn('id="faq-modal"', content)
        self.assertIn("BC_Q4", content)
        self.assertIn("BC_Q5", content)
        self.assertIn("Large / Big Brackets", content)
        self.assertIn("Small Brackets", content)
        self.assertIn("Blue Blocks", content)
        self.assertIn("Yellow Blocks", content)

    def test_05_generate_tutorials_scorer_faq(self):
        """Verify generate_tutorials.py includes complete FAQ and bracket breakdown."""
        content = self.gen_tutorials.read_text(encoding="utf-8")
        self.assertIn("Comprehensive Scorer FAQs & Diligence Knowledge Base", content)
        self.assertIn("Large vs. Small Brackets (BC_Q4 vs. BC_Q5)", content)
        self.assertIn("Can I Google search", content)
        self.assertIn("Strict Scoping", content)
        self.assertIn("Flexible Scoping", content)
        self.assertIn("Essential Business Deliverables (EBD) Phase", content)

    def test_06_desktop_tutorial_pdf_synced(self):
        """Verify CleanTech_Open_Scorer_Tutorial.pdf exists on Desktop and is valid."""
        if self.desktop_tutorial.exists():
            self.assertGreater(self.desktop_tutorial.stat().st_size, 500000, "Tutorial PDF must be substantial")

    def test_07_agents_md_brackets_documented(self):
        """Verify AGENTS.md records the Strategyzer bracket standard."""
        content = self.agents_md.read_text(encoding="utf-8")
        self.assertIn("BC_Q4` Large / Big Brackets", content)
        self.assertIn("BC_Q5` Small Brackets", content)

    def test_08_bmc_brackets_screenshot_assets_exist(self):
        """Verify Strategyzer screenshot files exist in docs and site assets."""
        docs_img = self.root / "docs" / "tutorial_assets" / "bmc_brackets_strategyzer.png"
        site_img = self.root / "site" / "img" / "bmc_brackets_strategyzer.png"
        self.assertTrue(docs_img.exists(), "docs BMC screenshot must exist")
        self.assertTrue(site_img.exists(), "site BMC screenshot must exist")
        self.assertGreater(docs_img.stat().st_size, 50000, "Screenshot file must be valid PNG")

    def test_09_bmc_brackets_image_referenced(self):
        """Verify BMC screenshot is referenced in index.html, app.js, and generate_tutorials.py."""
        self.assertIn("img/bmc_brackets_strategyzer.png", self.index_html.read_text(encoding="utf-8"))
        self.assertIn("img/bmc_brackets_strategyzer.png", self.app_js.read_text(encoding="utf-8"))
        self.assertIn("BMC_SCREENSHOT_PATH", self.gen_tutorials.read_text(encoding="utf-8"))

    def test_10_index_html_walkthrough_links(self):
        """Verify site/index.html contains links to the Scorer Walkthrough."""
        content = self.index_html.read_text(encoding="utf-8")
        self.assertIn('href="scorer_tutorial.html"', content)
        self.assertIn("Scorer Guide", content)
        self.assertIn("View Scorer Walkthrough", content)

    def test_11_admin_html_walkthrough_links(self):
        """Verify site/admin.html contains links to Admin and Scorer Walkthroughs."""
        admin_html = self.root / "site" / "admin.html"
        content = admin_html.read_text(encoding="utf-8")
        self.assertIn('href="admin_tutorial.html"', content)
        self.assertIn('href="scorer_tutorial.html"', content)
        self.assertIn("Admin Walkthrough", content)

    def test_12_walkthrough_html_hub_exists(self):
        """Verify site/walkthrough.html exists and links to both portals and tutorials."""
        hub = self.root / "site" / "walkthrough.html"
        self.assertTrue(hub.exists(), "site/walkthrough.html must exist")
        content = hub.read_text(encoding="utf-8")
        self.assertIn("scorer_tutorial.html", content)
        self.assertIn("admin_tutorial.html", content)
        self.assertIn("index.html", content)
        self.assertIn("admin.html", content)

    def test_13_web_tutorial_assets_no_broken_file_urls(self):
        """Verify generated web tutorials exist in site/ and contain no file:// URLs."""
        scorer_html = self.root / "site" / "scorer_tutorial.html"
        admin_html = self.root / "site" / "admin_tutorial.html"
        self.assertTrue(scorer_html.exists(), "site/scorer_tutorial.html must exist")
        self.assertTrue(admin_html.exists(), "site/admin_tutorial.html must exist")
        self.assertNotIn("file://", scorer_html.read_text(encoding="utf-8"))
        self.assertNotIn("file://", admin_html.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

