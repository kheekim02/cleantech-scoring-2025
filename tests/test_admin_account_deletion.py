"""Unit tests for Admin Account Deletion capability."""
import unittest
from pathlib import Path


class TestAdminAccountDeletion(unittest.TestCase):
    """Verify backend and frontend support for deleting scorer accounts."""

    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.admin_actions_js = self.root / "api" / "admin-actions.js"
        self.admin_js = self.root / "site" / "js" / "admin.js"

    def test_01_backend_delete_judge_action_exists(self):
        """Verify api/admin-actions.js handles DELETE_JUDGE action."""
        self.assertTrue(self.admin_actions_js.exists(), "api/admin-actions.js must exist")
        content = self.admin_actions_js.read_text(encoding="utf-8")
        self.assertIn("DELETE_JUDGE", content, "admin-actions.js must handle DELETE_JUDGE action")
        self.assertIn("DELETE FROM judges WHERE judge_id = $1", content, "admin-actions.js must delete from judges table")
        self.assertIn("DELETE FROM judge_assignments WHERE judge_id = $1", content, "admin-actions.js must delete judge assignments")
        self.assertIn("DELETE FROM auth_sessions", content, "admin-actions.js must clear judge sessions")
        self.assertIn("SCORER_DELETED", content, "admin-actions.js must record deletion in audit log")

    def test_02_frontend_delete_scorer_method_exists(self):
        """Verify site/js/admin.js implements deleteScorer with confirm and API call."""
        self.assertTrue(self.admin_js.exists(), "site/js/admin.js must exist")
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("deleteScorer(", content, "admin.js must define deleteScorer method")
        self.assertIn("confirm(", content, "deleteScorer must prompt user for confirmation")
        self.assertIn("DELETE_JUDGE", content, "deleteScorer must dispatch DELETE_JUDGE action")

    def test_03_frontend_render_scorers_includes_delete_button(self):
        """Verify renderScorers renders a delete button for each scorer item."""
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("btn-delete-scorer", content, "renderScorers must render delete button with class btn-delete-scorer")
        self.assertIn("AdminApp.deleteScorer", content, "delete button must invoke AdminApp.deleteScorer")

    def test_04_backend_reset_judge_password_action_exists(self):
        """Verify api/admin-actions.js handles RESET_JUDGE_PASSWORD action."""
        content = self.admin_actions_js.read_text(encoding="utf-8")
        self.assertIn("RESET_JUDGE_PASSWORD", content)
        self.assertIn("UPDATE judges SET password_hash = $1 WHERE judge_id = $2", content)
        self.assertIn("SCORER_PASSWORD_RESET", content)

    def test_05_frontend_reset_password_method_and_button_exists(self):
        """Verify site/js/admin.js implements resetPassword and renders Reset Pass button."""
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("resetPassword(", content)
        self.assertIn("RESET_JUDGE_PASSWORD", content)
        self.assertIn("btn-reset-pass", content)
        self.assertIn("AdminApp.resetPassword", content)

    def test_06_backend_export_scores_endpoint_exists(self):
        """Verify api/export-scores.js exists and formats CSV output."""
        export_api = self.root / "api" / "export-scores.js"
        self.assertTrue(export_api.exists())
        content = export_api.read_text(encoding="utf-8")
        self.assertIn("text/csv", content)
        self.assertIn("human_reviews", content)
        self.assertIn("requireSession", content)

    def test_07_frontend_export_scores_button_and_method_exists(self):
        """Verify site/admin.html and site/js/admin.js have export scores button and method."""
        admin_html = (self.root / "site" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("AdminApp.exportScores()", admin_html)
        content = self.admin_js.read_text(encoding="utf-8")
        self.assertIn("exportScores()", content)
        self.assertIn("/api/export-scores", content)

    def test_08_cli_export_scores_script_exists(self):
        """Verify scripts/export_scored_data.py exists and defines export_scores function."""
        export_script = self.root / "scripts" / "export_scored_data.py"
        self.assertTrue(export_script.exists())
        content = export_script.read_text(encoding="utf-8")
        self.assertIn("def export_scores(", content)


if __name__ == "__main__":
    unittest.main()
