"""Unit tests for frontend citation jump without bounding box overhead.

Human-only UI: AI dossier / .link-source listeners are removed from app.js.
jumpToCitation remains available on CTO.Render for deliverable navigation.
"""
import re
import unittest
from pathlib import Path


class TestFrontendCitationJump(unittest.TestCase):
    def setUp(self):
        self.render_js_path = Path("site/js/render.js")
        self.app_js_path = Path("site/js/app.js")
        self.assertTrue(self.render_js_path.exists(), "render.js must exist")
        self.assertTrue(self.app_js_path.exists(), "app.js must exist")
        with open(self.render_js_path, "r", encoding="utf-8") as f:
            self.render_js = f.read()
        with open(self.app_js_path, "r", encoding="utf-8") as f:
            self.app_js = f.read()

    def test_01_no_bbox_data_attribute_in_render(self):
        """Verify render.js does not render unnecessary data-bbox attributes."""
        self.assertNotIn("data-bbox", self.render_js, "render.js should not render data-bbox attribute")

    def test_02_no_bbox_badge_in_citation(self):
        """Verify render.js eliminates bbox coordinate badge."""
        self.assertNotIn("hasBboxCoords", self.render_js, "render.js should not compute hasBboxCoords")
        self.assertNotIn("bboxBadge", self.render_js, "render.js should not render bboxBadge")

    def test_03_jump_to_citation_signature(self):
        """Verify jumpToCitation accepts clean (pdfFilename, pageNumber) arguments."""
        self.assertTrue(
            re.search(r"jumpToCitation\s*\(\s*pdfFilename\s*,\s*pageNumber\s*\)", self.render_js) is not None,
            "jumpToCitation should accept clean (pdfFilename, pageNumber) signature"
        )
        self.assertNotIn("viewrect=", self.render_js, "jumpToCitation should not append viewrect parameter")

    def test_04_app_js_has_no_ai_dossier_link_source_listeners(self):
        """Verify AI dossier .link-source handlers are absent from app.js."""
        self.assertNotIn("link.dataset.bbox", self.app_js)
        self.assertNotIn(".link-source", self.app_js)
        self.assertNotIn("AI Diligence Dossier", self.app_js)
        self.assertNotIn("data-action=\"jump-pdf\"", self.app_js)
        self.assertNotIn(
            "CTO.Render.jumpToCitation(link.dataset.pdf, link.dataset.page)",
            self.app_js,
            "app.js must not wire dossier auto-jump from .link-source",
        )

    def test_05_render_exposes_jump_to_citation(self):
        """Verify CTO.Render.jumpToCitation(pdfFilename, pageNumber) remains for PDF nav."""
        self.assertTrue(
            re.search(r"jumpToCitation\s*\(\s*pdfFilename\s*,\s*pageNumber\s*\)", self.render_js) is not None,
            "CTO.Render.jumpToCitation(pdfFilename, pageNumber) must remain on render.js",
        )

    def test_06_clean_citation_page_jump(self):
        """Verify jumpToCitation sets page hash directly."""
        self.assertIn("#page=${pageNumber}", self.render_js)
        self.assertIn("navpanes=0&pagemode=none", self.render_js)

    def test_07_render_has_no_ai_dossier_ui(self):
        """Verify render.js no longer builds AI suggestion / dossier chrome."""
        self.assertNotIn("showAiAssist", self.render_js)
        self.assertNotIn("AI Diligence Dossier", self.render_js)
        self.assertNotIn("h-ai-suggest", self.render_js)
        self.assertNotIn("link-source", self.render_js)


if __name__ == "__main__":
    unittest.main()
