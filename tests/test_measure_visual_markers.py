# tests/test_measure_visual_markers.py
import unittest
from scripts.measure_visual_markers import count_visual_markers


class TestVisualMarkers(unittest.TestCase):
    def test_counts_marker_families(self):
        text = "<!-- image -->\n![fig](a.png)\n## Diagram\nFigure 2: Process flow\nplain text"
        c = count_visual_markers(text)
        self.assertEqual(c["image_comment"], 1)
        self.assertEqual(c["md_image"], 1)
        self.assertEqual(c["diagram_heading"], 1)
        self.assertEqual(c["figure_caption"], 1)

    def test_plain_prose_has_no_markers(self):
        self.assertEqual(sum(count_visual_markers("We use a schematic approach.").values()), 0)


if __name__ == "__main__":
    unittest.main()
