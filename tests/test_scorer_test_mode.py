"""Unit tests for Scorer Test / Admin Preview Mode."""
import unittest
from pathlib import Path


class TestScorerTestMode(unittest.TestCase):
    """Verify backend and frontend support for test / preview scorer accounts."""

    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.auth_js = self.root / "api" / "_auth.js"
        self.auth_login_js = self.root / "api" / "auth-login.js"
        self.auth_session_js = self.root / "api" / "auth-session.js"
        self.list_startups_js = self.root / "api" / "list-startups.js"
        self.get_startup_js = self.root / "api" / "get-startup.js"
        self.sync_scores_js = self.root / "api" / "sync-scores.js"
        self.admin_actions_js = self.root / "api" / "admin-actions.js"
        self.admin_data_js = self.root / "api" / "admin-data.js"
        self.export_scores_js = self.root / "api" / "export-scores.js"
        self.export_script = self.root / "scripts" / "export_scored_data.py"
        self.index_html = self.root / "site" / "index.html"
        self.app_js = self.root / "site" / "js" / "app.js"
        self.admin_html = self.root / "site" / "admin.html"
        self.admin_js = self.root / "site" / "js" / "admin.js"

    def test_01_auth_helper_exports_isTestScorer(self):
        """Verify api/_auth.js implements and exports isTestScorer."""
        content = self.auth_js.read_text(encoding="utf-8")
        self.assertIn("async function isTestScorer(client, principalId)", content)
        self.assertIn("isTestScorer,", content)
        self.assertIn("SELECT is_test FROM judges WHERE judge_id = $1", content)
        self.assertIn("SELECT 1 FROM admins WHERE username = $1", content)

    def test_02_auth_login_supports_test_mode_and_admin_fallback(self):
        """Verify api/auth-login.js flags is_test for test judges and admin accounts on scorer portal."""
        content = self.auth_login_js.read_text(encoding="utf-8")
        self.assertIn("SELECT password_hash, is_test FROM judges WHERE judge_id = $1", content)
        self.assertIn("isTest = !!judgeRes.rows[0].is_test;", content)
        self.assertIn("SELECT password_hash FROM admins WHERE username = $1", content)
        self.assertIn("is_test: isTest", content)

    def test_03_auth_session_returns_is_test(self):
        """Verify api/auth-session.js returns is_test flag in session user object."""
        content = self.auth_session_js.read_text(encoding="utf-8")
        self.assertIn("isTestScorer", content)
        self.assertIn("is_test: isTest", content)

    def test_04_list_startups_returns_all_companies_for_test_scorer(self):
        """Verify api/list-startups.js returns all cohort companies when isTestScorer is true."""
        content = self.list_startups_js.read_text(encoding="utf-8")
        self.assertIn("isTestScorer", content)
        self.assertIn("if (isTest)", content)
        self.assertIn("SELECT startup_id as id, company_name as name FROM startup_extractions", content)

    def test_05_get_startup_bypasses_assignment_and_omits_db_reviews_for_test_scorer(self):
        """Verify api/get-startup.js allows unassigned startup access and omits reviews for test scorer."""
        content = self.get_startup_js.read_text(encoding="utf-8")
        project = (self.root / "api" / "_project_startup.js").read_text(encoding="utf-8")
        self.assertIn("isTestScorer", content)
        self.assertIn("if (!isTest)", content)
        self.assertIn("applyHumanProjectionInPlace", content)
        self.assertIn("payload.judge_reviews = reviewsRows", project)
        self.assertIn("payload.is_test = isTest", project)

    def test_05b_get_startup_projects_human_only_questions(self):
        """Verify get-startup strips AI fields via shared human-only projection."""
        content = self.get_startup_js.read_text(encoding="utf-8")
        project = (self.root / "api" / "_project_startup.js").read_text(encoding="utf-8")
        self.assertIn("applyHumanProjectionInPlace", content)
        self.assertIn("delete payload.ai_cats", project)
        for forbidden in (
            "ai_suggestion",
            "ai_confidence",
            "ai_rationale",
            "verbatim_citation",
            "source_pdf",
            "page_number",
        ):
            self.assertNotRegex(
                project,
                rf"{forbidden}\s*:",
                f"projection must not include {forbidden}",
            )

    def test_06_sync_scores_intercepts_writes_for_test_scorer(self):
        """Verify api/sync-scores.js prevents writing to human_reviews for test accounts."""
        content = self.sync_scores_js.read_text(encoding="utf-8")
        self.assertIn("isTestScorer", content)
        self.assertIn("if (isTest)", content)
        self.assertIn("test_mode: true", content)
        self.assertIn("Scores are not persisted to database", content)

    def test_06b_sync_scores_overwrites_justification_on_clear(self):
        """Empty justification must overwrite DB text (no COALESCE on justification)."""
        content = self.sync_scores_js.read_text(encoding="utf-8")
        self.assertIn("justification = EXCLUDED.justification", content)
        self.assertNotIn(
            "justification = COALESCE(EXCLUDED.justification, human_reviews.justification)",
            content,
        )
        self.assertIn("String(item.justification ?? '').trim()", content)

    def test_06c_sync_scores_uses_unnest_and_rubric_not_payload(self):
        """Batch upsert via UNNEST; validate against master_282_rubric.json, not payload JSONB."""
        content = self.sync_scores_js.read_text(encoding="utf-8")
        self.assertIn("UNNEST", content)
        self.assertIn("master_282_rubric.json", content)
        self.assertIn("SELECT 1 FROM startup_extractions WHERE startup_id = $1", content)
        self.assertNotIn("SELECT payload FROM startup_extractions", content)
        # Per-row INSERT … VALUES ($1..$6) loop must be gone.
        self.assertNotIn("VALUES ($1, $2, $3, $4, $5, COALESCE($6, FALSE))", content)
        self.assertIn("FROM UNNEST(", content)

    def test_07_admin_actions_create_judge_handles_is_test(self):
        """Verify api/admin-actions.js accepts and persists is_test in CREATE_JUDGE."""
        content = self.admin_actions_js.read_text(encoding="utf-8")
        self.assertIn("new_judge_id, new_password, is_test", content)
        self.assertIn("INSERT INTO judges (judge_id, passcode, password_hash, is_test)", content)

    def test_08_admin_data_selects_is_test(self):
        """Verify api/admin-data.js queries is_test column from judges table."""
        content = self.admin_data_js.read_text(encoding="utf-8")
        self.assertIn("SELECT judge_id, is_test FROM judges", content)

    def test_09_export_scores_filters_out_test_judges(self):
        """Verify CSV export queries exclude test judges."""
        api_content = self.export_scores_js.read_text(encoding="utf-8")
        self.assertIn("hr.judge_id NOT IN (SELECT judge_id FROM judges WHERE is_test = true)", api_content)

        script_content = self.export_script.read_text(encoding="utf-8")
        self.assertIn("hr.judge_id NOT IN (SELECT judge_id FROM judges WHERE is_test = TRUE)", script_content)

    def test_10_index_html_has_test_mode_banner(self):
        """Verify site/index.html includes the test-mode-banner markup."""
        content = self.index_html.read_text(encoding="utf-8")
        self.assertIn('id="test-mode-banner"', content)
        self.assertIn("Test & Admin Preview Mode", content)

    def test_11_app_js_handles_test_mode_ui(self):
        """Verify site/js/app.js handles test mode banner without disruptive navbar label."""
        content = self.app_js.read_text(encoding="utf-8")
        self.assertIn("applyUserRoleUI", content)
        self.assertIn("test-mode-banner", content)
        self.assertNotIn("Test Mode (No DB Save)", content, "Disruptive navbar label must not be injected")

    def test_12_admin_ui_has_test_mode_checkbox_and_badges(self):
        """Verify site/admin.html and site/js/admin.js allow creating and viewing test accounts."""
        html_content = self.admin_html.read_text(encoding="utf-8")
        self.assertIn('id="new-judge-test"', html_content)
        self.assertIn("Test / Preview Mode", html_content)

        js_content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("new-judge-test", js_content)
        self.assertIn("Test Mode", js_content)
        self.assertIn("Test Account · Views all companies, no DB writes", js_content)


if __name__ == "__main__":
    unittest.main()
