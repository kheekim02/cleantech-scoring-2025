# tests/test_visual_deck_inspector.py
import unittest
import fitz
import tempfile
from pathlib import Path
from src.scorer.visual_deck_inspector import inspect_deck_visuals


class TestVisualDeckInspector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf_path = Path(self.tmp.name) / "test_deck.pdf"
        doc = fitz.open()

        # Page 1: Title slide with a logo-like small image / rect
        p1 = doc.new_page(width=1920, height=1080)
        p1.draw_rect(fitz.Rect(50, 50, 250, 150), color=(0, 0, 1), fill=(0, 0.5, 1))

        # Page 2: Problem slide with a flowchart / vector diagram (multiple connected rects)
        p2 = doc.new_page(width=1920, height=1080)
        p2.insert_text((100, 100), "The Problem: Inefficient Grid Storage")
        # Draw 5 connected shapes resembling a flowchart
        for i in range(5):
            p2.draw_rect(fitz.Rect(100 + i * 250, 300, 300 + i * 250, 450), color=(1, 0, 0))
            if i < 4:
                p2.draw_line((300 + i * 250, 375), (350 + i * 250, 375), color=(0, 0, 0))

        # Page 3: Pure text slide
        p3 = doc.new_page(width=1920, height=1080)
        p3.insert_text((100, 100), "Financial Projections Summary Table")

        doc.save(str(self.pdf_path))
        doc.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_inspect_deck_visuals(self):
        result = inspect_deck_visuals(self.pdf_path)
        self.assertEqual(result["page_count"], 3)
        self.assertTrue(result["has_vector_drawings"])
        # Page 2 should be flagged as containing a diagram/model
        p2_info = result["pages"][1]
        self.assertGreater(p2_info["drawing_count"], 5)
        self.assertTrue(p2_info["is_diagram_candidate"])

        # Page 1 has logo candidate
        p1_info = result["pages"][0]
        self.assertTrue(p1_info["has_logo_candidate"])


if __name__ == "__main__":
    unittest.main()
