"""Client bootstrap orchestration tests (string/source contracts)."""
import unittest
from pathlib import Path


class TestAppBootstrap(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.app_js = (self.root / "site" / "js" / "app.js").read_text(encoding="utf-8")
        self.index = (self.root / "site" / "index.html").read_text(encoding="utf-8")

    def test_01_init_uses_bootstrap_not_waterfall(self):
        self.assertIn("fetch(`/api/bootstrap${qs}`)", self.app_js)
        self.assertIn("applyBootstrapPayload", self.app_js)
        # Initial hydrate must not chain auth-session then list-startups.
        init_block = self.app_js.split("init() {", 1)[1].split("applyUserRoleUI()", 1)[0]
        self.assertNotIn("/api/auth-session", init_block)
        self.assertNotIn("/api/list-startups", init_block)

    def test_02_login_also_bootstraps(self):
        self.assertIn("handleLogin()", self.app_js)
        self.assertIn("/api/bootstrap", self.app_js)
        login = self.app_js.split("async handleLogin()", 1)[1].split("async loadStartupsList", 1)[0]
        self.assertIn("/api/bootstrap", login)

    def test_03_picker_still_uses_get_startup_for_switch(self):
        self.assertIn("this.startApp()", self.app_js)
        self.assertIn("/api/get-startup?id=", self.app_js)

    def test_04_storage_preconnect_and_cache_buster(self):
        self.assertIn("rel=\"preconnect\"", self.index)
        self.assertIn("ubuqkdhajnnagropmatv.supabase.co", self.index)
        self.assertIn("app.js?v=30", self.index)
        self.assertIn("style.css?v=30", self.index)


if __name__ == "__main__":
    unittest.main()
