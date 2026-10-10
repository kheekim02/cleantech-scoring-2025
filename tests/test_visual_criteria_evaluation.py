# tests/test_visual_criteria_evaluation.py
import unittest
from src.scorer.visual_deck_inspector import inspect_deck_visuals
from src.scorer.deterministic_evaluator import evaluate_visual_criterion
import fitz
import tempfile
from pathlib import Path


class TestVisualCriteriaEvaluation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf_path = Path(self.tmp.name) / "08_PitchDeck.pdf"
        doc = fitz.open()

        # Slide 1: Logo
        p1 = doc.new_page(width=1920, height=1080)
        p1.draw_rect(fitz.Rect(50, 50, 300, 180), color=(0, 0, 1), fill=(0, 0.5, 1))

        # Slide 2: Problem model with diagram
        p2 = doc.new_page(width=1920, height=1080)
        p2.insert_text((100, 100), "The Challenge: Grid Overload")
        for i in range(6):
            p2.draw_rect(fitz.Rect(100 + i * 200, 300, 250 + i * 200, 450), color=(1, 0, 0))

        doc.save(str(self.pdf_path))
        doc.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_evaluate_ip_q7_problem_model(self):
        deck_meta = inspect_deck_visuals(self.pdf_path)
        rec = evaluate_visual_criterion("IP_Q7", deck_meta, startup_id="TestCo")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["predicted_val"], 1.0)
        self.assertIn("slide 2", rec["citation"].lower())
        self.assertEqual(rec["source"], "visual_inspection")

    def test_evaluate_pmf_q24_billboard_logo(self):
        deck_meta = inspect_deck_visuals(self.pdf_path)
        rec = evaluate_visual_criterion("PMF_Q24", deck_meta, startup_id="TestCo")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["predicted_val"], 1.0)
        self.assertIn("slide 1", rec["citation"].lower())
        self.assertEqual(rec["source"], "visual_inspection")


if __name__ == "__main__":
    unittest.main()
