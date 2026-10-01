"""Unit tests for shared serverless Postgres pool module."""
import unittest
from pathlib import Path


class TestDbPool(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.db_js = self.root / "api" / "_db.js"

    def test_01_db_module_exists_and_exports_pool(self):
        content = self.db_js.read_text(encoding="utf-8")
        self.assertIn("new Pool(", content)
        self.assertIn("max: 5", content)
        self.assertIn("idleTimeoutMillis: 30000", content)
        self.assertIn("rejectUnauthorized: false", content)
        self.assertIn("function query(", content)
        self.assertIn("module.exports", content)
        self.assertIn("getPool", content)

    def test_02_core_handlers_use_shared_pool(self):
        handlers = [
            "auth-session.js",
            "auth-login.js",
            "list-startups.js",
            "get-startup.js",
            "sync-scores.js",
            "bootstrap.js",
            "admin-data.js",
            "export-scores.js",
        ]
        for name in handlers:
            content = (self.root / "api" / name).read_text(encoding="utf-8")
            self.assertIn("require('./_db')", content, f"{name} must use shared pool")
            self.assertNotIn("new Client(", content, f"{name} must not create Client")


if __name__ == "__main__":
    unittest.main()
