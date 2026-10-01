"""Unit tests for Split-Pane Resizer functionality in Scorer Portal."""
import unittest
from pathlib import Path


class TestSplitPaneResizer(unittest.TestCase):
    """Verify markup, styling, and client-side behavior for draggable split-pane resizer."""

    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.index_html = self.root / "site" / "index.html"
        self.style_css = self.root / "site" / "style.css"
        self.app_js = self.root / "site" / "js" / "app.js"
        self.assertTrue(self.index_html.exists(), "site/index.html must exist")
        self.assertTrue(self.style_css.exists(), "site/style.css must exist")
        self.assertTrue(self.app_js.exists(), "site/js/app.js must exist")

    def test_01_index_html_has_resizer_markup(self):
        """Verify site/index.html contains the pane-resizer separator between panels."""
        content = self.index_html.read_text(encoding="utf-8")
        self.assertIn('id="pane-resizer"', content)
        self.assertIn('class="pane-resizer"', content)
        self.assertIn('role="separator"', content)
        self.assertIn('aria-orientation="vertical"', content)
        self.assertIn('class="resizer-handle"', content)
        self.assertIn('id="right-pane"', content)
        self.assertIn('style.css?v=26', content)
        self.assertIn('js/app.js?v=26', content)

    def test_02_css_supports_resizer_and_variable_widths(self):
        """Verify site/style.css defines custom property width, clamping, and pointer styles."""
        content = self.style_css.read_text(encoding="utf-8")
        self.assertIn("--left-pane-width", content)
        self.assertIn("min-width: 360px", content)
        self.assertIn("max-width: calc(100% - 360px)", content)
        self.assertIn(".pane-resizer", content)
        self.assertIn("cursor: col-resize", content)
        self.assertIn(".resizer-handle", content)
        self.assertIn("body.is-resizing", content)
        self.assertIn("body.is-resizing #primary-pdf-viewer", content)
        self.assertIn("pointer-events: none !important", content)

    def test_03_app_js_implements_setup_pane_resizer(self):
        """Verify site/js/app.js implements draggable resizing, persistence, and double-click reset."""
        content = self.app_js.read_text(encoding="utf-8")
        self.assertIn("this.setupPaneResizer()", content)
        self.assertIn("setupPaneResizer()", content)
        self.assertIn("cto_left_pane_width", content)
        self.assertIn("localStorage.getItem('cto_left_pane_width')", content)
        self.assertIn("localStorage.setItem('cto_left_pane_width'", content)
        self.assertIn("setPointerCapture", content)
        self.assertIn("is-resizing", content)
        self.assertIn("dblclick", content)
        self.assertIn("localStorage.removeItem('cto_left_pane_width')", content)
        self.assertIn("360", content, "Resizer must clamp at 360px minimum width")


if __name__ == "__main__":
    unittest.main()
