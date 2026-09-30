"""Unit tests for Cohort 2x Diligence Coverage Hub and Admin Progress Expansion."""
import unittest
from pathlib import Path


class TestCohort2xCoverage(unittest.TestCase):
    """Verify backend and frontend support for Cohort 2x Diligence Coverage and accurate tracking."""

    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.admin_data_js = self.root / "api" / "admin-data.js"
        self.admin_html = self.root / "site" / "admin.html"
        self.admin_js = self.root / "site" / "js" / "admin.js"

    def test_01_backend_admin_data_accurate_counts_and_timestamp(self):
        """Verify api/admin-data.js queries accurate non-null score counts, flagged counts, and last_saved."""
        self.assertTrue(self.admin_data_js.exists(), "api/admin-data.js must exist")
        content = self.admin_data_js.read_text(encoding="utf-8")
        self.assertIn("score_value IS NOT NULL THEN 1 END)::int as answered_count", content)
        self.assertIn("is_flagged = TRUE THEN 1 END)::int as flagged_count", content)
        self.assertIn("MAX(updated_at) as last_saved", content)

    def test_02_admin_html_has_cohort_coverage_section(self):
        """Verify site/admin.html includes the Cohort 2x Diligence Coverage Hub markup."""
        self.assertTrue(self.admin_html.exists(), "site/admin.html must exist")
        content = self.admin_html.read_text(encoding="utf-8")
        self.assertIn('id="cohort-coverage-section"', content)
        self.assertIn("Cohort 2x Diligence Coverage Hub", content)
        self.assertIn('id="coverage-kanban-grid"', content)
        self.assertIn('id="lane-1"', content)
        self.assertIn('id="lane-2"', content)
        self.assertIn('id="lane-3"', content)
        self.assertIn('id="coverage-search-input"', content)

    def test_03_admin_html_has_kpi_strip(self):
        """Verify site/admin.html includes coverage KPI metrics strip."""
        content = self.admin_html.read_text(encoding="utf-8")
        self.assertIn('id="kpi-total-startups"', content)
        self.assertIn('id="kpi-2x-scored"', content)
        self.assertIn('id="kpi-1x-scored"', content)
        self.assertIn('id="kpi-in-prog"', content)
        self.assertIn('id="kpi-unassigned"', content)
        self.assertIn('id="kpi-assignment-coverage"', content)

    def test_04_admin_html_has_quick_assign_modal(self):
        """Verify site/admin.html includes Quick Assign modal."""
        content = self.admin_html.read_text(encoding="utf-8")
        self.assertIn('id="quick-assign-modal"', content)
        self.assertIn('id="qa-startup-id"', content)
        self.assertIn('id="qa-judge-select"', content)
        self.assertIn("AdminApp.confirmQuickAssign()", content)

    def test_05_admin_js_implements_coverage_methods(self):
        """Verify site/js/admin.js implements renderCoverageBoard and filter/search methods."""
        self.assertTrue(self.admin_js.exists(), "site/js/admin.js must exist")
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("renderCoverageBoard()", content)
        self.assertIn("setCoverageFilter(", content)
        self.assertIn("setCoverageSearch(", content)
        self.assertIn("openAssignModal(", content)
        self.assertIn("closeAssignModal()", content)
        self.assertIn("confirmQuickAssign()", content)

    def test_06_admin_js_implements_time_helpers(self):
        """Verify site/js/admin.js implements relative and full date formatting helpers."""
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("formatTimeAgo(", content)
        self.assertIn("formatFullDateTime(", content)

    def test_07_admin_js_toggle_assignment_refreshes_coverage(self):
        """Verify toggleAssignment triggers both assignment and coverage board re-renders."""
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("this.renderAssignments();", content)
        self.assertIn("this.renderCoverageBoard();", content)

    def test_08_admin_js_assignment_list_shows_282_and_timestamp(self):
        """Verify renderAssignments displays progress out of 282 and last saved timestamp."""
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("282 Answers", content)
        self.assertIn("Completed (282/282)", content)
        self.assertIn("Not Started (0/282)", content)
        self.assertIn("this.formatTimeAgo(pSaved)", content)

    def test_09_admin_js_scorers_list_shows_last_active(self):
        """Verify renderScorers calculates and renders scorer last active timing."""
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("Last active:", content)
        self.assertIn("Password protected", content)

    def test_10_api_export_scores_only_retains_clean_evaluation_columns(self):
        """Verify api/export-scores.js removed legacy AI columns and retains only relevant scoring columns."""
        export_api = self.root / "api" / "export-scores.js"
        self.assertTrue(export_api.exists())
        content = export_api.read_text(encoding="utf-8")

        legacy_ai_cols = [
            "AI Suggestion",
            "AI Confidence",
            "AI Concordance",
            "AI Rationale",
            "Source Deliverable",
            "Citation Page",
            "Verbatim Citation",
        ]
        for col in legacy_ai_cols:
            self.assertNotIn(col, content, f"api/export-scores.js must not contain legacy column '{col}'")

        required_cols = [
            "Startup ID",
            "Company Name",
            "Judge ID",
            "Category Code",
            "Category Name",
            "Question ID",
            "Question Text",
            "Score",
            "Justification",
            "Flagged for Review",
            "Scored At",
        ]
        for col in required_cols:
            self.assertIn(col, content, f"api/export-scores.js must contain clean column '{col}'")

    def test_11_cli_export_scores_only_retains_clean_evaluation_columns(self):
        """Verify scripts/export_scored_data.py removed legacy AI columns and retains only relevant scoring columns."""
        export_script = self.root / "scripts" / "export_scored_data.py"
        self.assertTrue(export_script.exists())
        content = export_script.read_text(encoding="utf-8")

        legacy_ai_cols = [
            "AI Suggestion",
            "AI Confidence",
            "AI Concordance",
            "AI Rationale",
            "Source Deliverable",
            "Citation Page",
            "Verbatim Citation",
        ]
        for col in legacy_ai_cols:
            self.assertNotIn(col, content, f"scripts/export_scored_data.py must not contain legacy column '{col}'")

        required_cols = [
            "Startup ID",
            "Company Name",
            "Judge ID",
            "Category Code",
            "Category Name",
            "Question ID",
            "Question Text",
            "Score",
            "Justification",
            "Flagged for Review",
            "Scored At",
        ]
        for col in required_cols:
            self.assertIn(col, content, f"scripts/export_scored_data.py must contain clean column '{col}'")


if __name__ == "__main__":
    unittest.main()

