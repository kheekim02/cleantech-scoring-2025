"""Security verification tests for Supabase PostgreSQL Row Level Security (RLS) and public schema hardening."""
import os
import unittest
import psycopg2
from dotenv import load_dotenv

load_dotenv()

PUBLIC_TABLES = [
    "admins",
    "auth_audit_log",
    "auth_sessions",
    "human_reviews",
    "judge_assignments",
    "judges",
    "scorer_feedback",
    "startup_extractions",
]


class TestSupabaseRLSSecurity(unittest.TestCase):
    """Verify that Row Level Security is active and PostgREST public access is locked down."""

    @classmethod
    def setUpClass(cls):
        dsn = os.environ.get("DATABASE_URL", "").split("?")[0]
        if not dsn:
            raise unittest.SkipTest("DATABASE_URL is not set")
        cls.conn = psycopg2.connect(dsn)
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "cur") and cls.cur:
            cls.cur.close()
        if hasattr(cls, "conn") and cls.conn:
            cls.conn.close()

    def test_01_all_public_tables_have_rls_enabled(self):
        """Verify every table in the public schema has rowsecurity = True (RLS enabled)."""
        self.cur.execute("""
            SELECT tablename, rowsecurity 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        rows = self.cur.fetchall()
        table_rls = {r[0]: r[1] for r in rows}

        disabled_tables = []
        for tbl in PUBLIC_TABLES:
            self.assertIn(tbl, table_rls, f"Table {tbl} must exist in public schema")
            if not table_rls[tbl]:
                disabled_tables.append(tbl)

        self.assertEqual(
            len(disabled_tables),
            0,
            f"The following public tables have RLS disabled: {disabled_tables}",
        )

    def test_02_zero_tables_fail_supabase_linter_rule_0013(self):
        """Simulate Supabase Database Linter rule 0013 (rls_disabled_in_public)."""
        self.cur.execute("""
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
              AND n.nspname = 'public'
              AND NOT c.relrowsecurity;
        """)
        flagged = [r[0] for r in self.cur.fetchall()]
        self.assertEqual(
            len(flagged),
            0,
            f"Tables failing Supabase Linter rule 0013 (RLS disabled in public): {flagged}",
        )

    def test_03_zero_grants_to_anon_and_authenticated_roles(self):
        """Verify that anon and authenticated roles have no table privileges in public schema."""
        self.cur.execute("""
            SELECT table_name, grantee, privilege_type
            FROM information_schema.role_table_grants
            WHERE table_schema = 'public' 
              AND grantee IN ('anon', 'authenticated')
            ORDER BY table_name, grantee, privilege_type;
        """)
        grants = self.cur.fetchall()
        self.assertEqual(
            len(grants),
            0,
            f"Found {len(grants)} active table grants to anon/authenticated roles: {grants[:5]}...",
        )

    def test_04_application_owner_retains_full_operational_access(self):
        """Verify the application connection (postgres owner role) can execute operations across all tables."""
        # 1. Read admins
        self.cur.execute("SELECT COUNT(*) FROM admins;")
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)

        # 2. Read judges
        self.cur.execute("SELECT COUNT(*) FROM judges;")
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)

        # 3. Read startup_extractions
        self.cur.execute("SELECT COUNT(*) FROM startup_extractions;")
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)

        # 4. Read judge_assignments
        self.cur.execute("SELECT COUNT(*) FROM judge_assignments;")
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)

        # 5. Read human_reviews
        self.cur.execute("SELECT COUNT(*) FROM human_reviews;")
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)

        # 6. Read auth_sessions
        self.cur.execute("SELECT COUNT(*) FROM auth_sessions;")
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)

        # 7. Read auth_audit_log
        self.cur.execute("SELECT COUNT(*) FROM auth_audit_log;")
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)

        # 8. Read scorer_feedback
        self.cur.execute("SELECT COUNT(*) FROM scorer_feedback;")
        self.assertGreaterEqual(self.cur.fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
