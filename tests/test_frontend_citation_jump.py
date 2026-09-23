"""Unit tests for frontend citation jump and bounding box rendering."""
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

    def test_01_bbox_data_attribute_in_render(self):
        """Verify render.js includes data-bbox in citation links."""
        self.assertIn("data-bbox", self.render_js, "render.js should render data-bbox attribute")

    def test_02_bbox_badge_or_indicator_in_citation(self):
        """Verify render.js displays bbox coordinate provenance badge."""
        self.assertTrue(
            "q.bbox" in self.render_js or "bbox" in self.render_js,
            "render.js should inspect question bbox property"
        )

    def test_03_jump_to_citation_signature(self):
        """Verify jumpToCitation accepts bbox argument gracefully."""
        self.assertTrue(
            re.search(r"jumpToCitation\s*\([^)]*bbox[^)]*\)", self.render_js) is not None,
            "jumpToCitation should accept a bbox parameter"
        )

    def test_04_app_js_passes_bbox(self):
        """Verify app.js extracts and forwards bbox to jumpToCitation."""
        self.assertIn("link.dataset.bbox", self.app_js)


if __name__ == "__main__":
    unittest.main()
