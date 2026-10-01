"""Deliverable viewer skeleton + stable iframe contracts."""
import unittest
from pathlib import Path


class TestDeliverableLoader(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.render = (self.root / "site" / "js" / "render.js").read_text(encoding="utf-8")
        self.css = (self.root / "site" / "style.css").read_text(encoding="utf-8")

    def test_01_stable_iframe_reuse(self):
        self.assertIn("existingIframe", self.render)
        self.assertIn("primary-pdf-viewer", self.render)
        self.assertIn("dataset.currentPdf", self.render)
        self.assertIn("#navpanes=0&pagemode=none", self.render)
        self.assertNotIn("#view=FitH", self.render)

    def test_02_skeleton_loader(self):
        self.assertIn("pdf-loading-skeleton", self.render)
        self.assertIn("onPdfLoaded", self.render)
        self.assertIn("pdf-loading-skeleton", self.css)
        self.assertIn("is-hidden", self.css)


if __name__ == "__main__":
    unittest.main()
