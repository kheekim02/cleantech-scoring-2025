"""Unit tests for unified /api/bootstrap endpoint and human-only projection."""
import unittest
from pathlib import Path


class TestBootstrapApi(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.bootstrap = (self.root / "api" / "bootstrap.js").read_text(encoding="utf-8")
        self.project = (self.root / "api" / "_project_startup.js").read_text(encoding="utf-8")
        self.get_startup = (self.root / "api" / "get-startup.js").read_text(encoding="utf-8")

    def test_01_bootstrap_exists_and_returns_consolidated_shape(self):
        self.assertIn("require('./_db')", self.bootstrap)
        self.assertIn("requireSession", self.bootstrap)
        self.assertIn("isTestScorer", self.bootstrap)
        self.assertIn("active_startup", self.bootstrap)
        self.assertIn("startups", self.bootstrap)
        self.assertIn("user:", self.bootstrap)
        self.assertIn("applyHumanProjectionInPlace", self.bootstrap)

    def test_02_bootstrap_respects_startup_id_query(self):
        self.assertIn("startup_id", self.bootstrap)
        self.assertIn("req.query", self.bootstrap)

    def test_03_shared_projection_strips_ai_fields(self):
        self.assertIn("applyHumanProjectionInPlace", self.project)
        self.assertIn("delete payload.ai_cats", self.project)
        self.assertIn("payload.judge_reviews = reviewsRows", self.project)
        self.assertIn("payload.is_test = isTest", self.project)
        for forbidden in (
            "ai_suggestion",
            "ai_confidence",
            "ai_rationale",
            "verbatim_citation",
            "source_pdf",
            "page_number",
        ):
            self.assertNotRegex(
                self.project,
                rf"{forbidden}\s*:",
                f"projection must not include {forbidden}",
            )

    def test_04_get_startup_reuses_shared_projection(self):
        self.assertIn("applyHumanProjectionInPlace", self.get_startup)
        self.assertIn(
            "applyHumanProjectionInPlace(payload, reviewsQuery.rows, isTest)",
            self.get_startup,
        )


if __name__ == "__main__":
    unittest.main()
