"""Runner script to apply scripts/migrations/20261006_enable_rls_and_revoke_public.sql."""
import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
MIGRATION_PATH = ROOT / "scripts" / "migrations" / "20261006_enable_rls_and_revoke_public.sql"


def main():
    dsn = os.environ.get("DATABASE_URL", "").split("?")[0]
    if not dsn:
        print("ERROR: DATABASE_URL not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    if not MIGRATION_PATH.is_file():
        print(f"ERROR: Migration file not found at {MIGRATION_PATH}", file=sys.stderr)
        sys.exit(1)

    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    print(f"Applying migration: {MIGRATION_PATH.name}...")

    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("Migration executed successfully.")

        # Inspect post-migration table status
        cur.execute("""
            SELECT tablename, rowsecurity 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        print("\nPublic schema tables status:")
        for tbl, rls in cur.fetchall():
            print(f"  {tbl:<25} | rowsecurity = {rls}")

        # Check remaining grants to anon and authenticated
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.role_table_grants 
            WHERE table_schema = 'public' 
              AND grantee IN ('anon', 'authenticated');
        """)
        anon_grants = cur.fetchone()[0]
        print(f"\nRemaining table grants to anon/authenticated: {anon_grants}")

        cur.close()
    except Exception as e:
        conn.rollback()
        print(f"ERROR applying migration: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
