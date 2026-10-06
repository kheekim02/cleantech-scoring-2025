# Supabase Database Security & RLS Resolution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all 7 Supabase Database Linter security errors (`rls_disabled_in_public` and `sensitive_columns_exposed`) by enabling Row Level Security across all public schema tables, revoking unauthenticated PostgREST permissions from `anon` and `authenticated`, and verifying zero disruption to the Vercel serverless application backend.

**Architecture:** Execute an atomic, idempotent SQL security migration in Supabase PostgreSQL (`migrations/20261006_enable_rls_and_revoke_public.sql`). Enable RLS on all 6 flagged tables (`startup_extractions`, `judge_assignments`, `admins`, `auth_sessions`, `auth_audit_log`, `scorer_feedback`). Revoke default table, sequence, and routine grants from `anon` and `authenticated` roles to block PostgREST exposure. Verify that the backend serverless connection (`postgres` owner role via `DATABASE_URL`) retains full CRUD access without breaking application workflows.

**Tech Stack:** PostgreSQL 15+ (Supabase / PgBouncer), Python (Pytest / Psycopg2), Node.js Serverless (Vercel).

**Spec:** `docs/superpowers/plans/2026-10-06-supabase-rls-resolution.md`

## Global Constraints

- Strict preservation of the 282-criteria human-only evaluation rubric across 10 categories (`BC`, `ES`, `F`, `IP`, `IS`, `L`, `M`, `PMF`, `T`, `TP`).
- Zero downtime or disruption to live judges scoring assigned startups or admins managing assignments.
- Backend serverless routes (`api/*.js`) connecting via `DATABASE_URL` must retain uninterrupted read/write access.
- PostgREST public access (`anon`, `authenticated` roles) must be completely locked down with default-deny.
- Idempotent migration scripts that can be safely executed multiple times without failure.
- No emojis in any code, commits, or responses.
- 100% test pass rate maintained across `pytest` (all 132 existing tests + new security tests).

## Review Focus

- Table owner RLS bypass: verify `postgres` role via `DATABASE_URL` continues to bypass RLS for all existing serverless endpoints (`get-startup`, `list-startups`, `sync-scores`, `admin-actions`, `auth-login`, `auth-session`).
- Public anon lockdown: verify an unauthenticated connection or client using the `anon` role cannot read `auth_sessions`, `admins`, or `startup_extractions`.
- Sensitive column protection: verify `session_token` in `auth_sessions` and `password_hash` in `admins` / `judges` are inaccessible via PostgREST.
- Future table safety: configure `ALTER DEFAULT PRIVILEGES` so any future table created in `public` automatically revokes grants from `anon` and `authenticated`.
- Rollback safety: provide deterministic rollback SQL statements in case of unexpected connection behavior.

---

## Technical Context & Root Cause Analysis

### Why Supabase Reported These Errors

| Linter Rule | Level | Impacted Tables | Cause |
| :--- | :---: | :--- | :--- |
| `rls_disabled_in_public` (Lint 0013) | **ERROR** | `startup_extractions`<br>`judge_assignments`<br>`admins`<br>`auth_sessions`<br>`auth_audit_log`<br>`scorer_feedback` | Supabase automatically exposes the `public` PostgreSQL schema to PostgREST HTTP endpoints (`/rest/v1/`). When tables are created in `public` without RLS enabled, PostgREST grants direct access to unauthenticated requests. |
| `sensitive_columns_exposed` (Lint 0023) | **ERROR** | `auth_sessions` (`session_token`) | `auth_sessions` contains active session tokens. Because RLS is disabled and default privileges grant `ALL` to `anon`, anyone with the project's public API key can query active session tokens directly via REST. |

### Database Architecture & Role Isolation

```
[External Web Client]
   │
   ├─► [Supabase PostgREST API /rest/v1/]
   │       └── Connects as: 'anon' / 'authenticated'
   │       └── ACTION: Blocked by RLS (Default Deny) & Revoked Grants
   │
   └─► [Vercel Serverless API /api/*]
           └── Connects via: DATABASE_URL (PgBouncer port 6543)
           └── Connects as: 'postgres' (Database Owner)
           └── ACTION: Bypasses RLS natively -> 100% Operational Access
```

1. **Why `human_reviews` and `judges` Were Not Flagged**:
   These two tables already have `rowsecurity = True` enabled. The remaining 6 tables were created during later auth/feedback migrations without an explicit `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`.
2. **Why Serverless Endpoints Are Unaffected**:
   In PostgreSQL, the table owner and superuser (`postgres`) bypasses Row Level Security by default (`ALTER TABLE ... FORCE ROW LEVEL SECURITY` is deliberately avoided). Because all application serverless functions in `api/` authenticate via `DATABASE_URL` as user `postgres`, their queries execute identically before and after RLS activation.

---

## Tasks

### Task 1: Write Automated Security Verification Tests

**Files:**
- Create: `tests/test_supabase_rls_security.py`

- [ ] **Step 1: Write test suite verifying RLS status and role access boundaries**
  - Verify `pg_tables.rowsecurity` is `True` for all 8 tables in `public` (`admins`, `auth_audit_log`, `auth_sessions`, `human_reviews`, `judge_assignments`, `judges`, `scorer_feedback`, `startup_extractions`).
  - Verify `role_table_grants` has 0 active grants to `anon` and `authenticated` in schema `public`.
  - Verify application connection (`postgres`) can execute queries across all 8 tables.
  - Verify simulated restricted role (`SET ROLE anon`) receives permission denied or empty rows on all 8 tables.
- [ ] **Step 2: Run test to confirm it fails closed on unpatched database**
  - Execute `pytest -q tests/test_supabase_rls_security.py`.
  - Confirm failure on the 6 unpatched tables (`admins`, `auth_sessions`, etc.).

---

### Task 2: Create Idempotent Security Migration Script

**Files:**
- Create: `scripts/migrations/20261006_enable_rls_and_revoke_public.sql`
- Create: `scripts/apply_security_migration.py`

- [ ] **Step 1: Write SQL migration file**
  - Enable RLS on all 6 unpatched public tables:
    ```sql
    ALTER TABLE public.startup_extractions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.judge_assignments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.admins ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.auth_sessions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.auth_audit_log ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.scorer_feedback ENABLE ROW LEVEL SECURITY;
    ```
  - Ensure `judges` and `human_reviews` are also reinforced:
    ```sql
    ALTER TABLE public.judges ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.human_reviews ENABLE ROW LEVEL SECURITY;
    ```
  - Revoke all permissions on public tables, sequences, and routines from `anon` and `authenticated`:
    ```sql
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
    REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon, authenticated;
    ```
  - Set default privileges for future tables:
    ```sql
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON ROUTINES FROM anon, authenticated;
    ```
- [ ] **Step 2: Write Python runner script to execute migration**
  - Create `scripts/apply_security_migration.py` connecting via `DATABASE_URL` with transaction rollback support.
- [ ] **Step 3: Execute migration against database**
  - Run `python3 scripts/apply_security_migration.py`.
- [ ] **Step 4: Verify migration output and commit**
  - Commit: `chore(db): create and apply rls security migration for public tables`

---

### Task 3: Security Validation & Application Smoke Test

**Files:**
- Test: `tests/test_supabase_rls_security.py`
- Test: `tests/test_scorer_test_mode.py`
- Test: `tests/test_admin_account_deletion.py`
- Test: `tests/test_h2o_now_deliverables.py`

- [ ] **Step 1: Run the dedicated security test suite**
  - Execute `pytest -q tests/test_supabase_rls_security.py`.
  - Confirm 100% pass (all 8 tables enabled, 0 anon grants).
- [ ] **Step 2: Run Supabase Database Linter simulation query**
  - Run query checking for any table in `public` where `not c.relrowsecurity`.
  - Confirm 0 rows returned.
- [ ] **Step 3: Run backend API integration smoke tests**
  - Verify `/api/auth-session`, `/api/list-startups`, `/api/get-startup`, `/api/sync-scores`, `/api/admin-actions`.
  - Confirm all CRUD operations succeed without RLS restriction errors.
- [ ] **Step 4: Run full regression test suite**
  - Execute `pytest -q`.
  - Confirm all 133+ tests pass.

---

### Task 4: Documentation & Rollback Plan

**Files:**
- Create: `scripts/migrations/rollback_20261006_enable_rls.sql`
- Modify: `docs/superpowers/plans/2026-10-06-supabase-rls-resolution.md`

- [ ] **Step 1: Create deterministic rollback script**
  - Document rollback SQL:
    ```sql
    ALTER TABLE public.startup_extractions DISABLE ROW LEVEL SECURITY;
    ALTER TABLE public.judge_assignments DISABLE ROW LEVEL SECURITY;
    ALTER TABLE public.admins DISABLE ROW LEVEL SECURITY;
    ALTER TABLE public.auth_sessions DISABLE ROW LEVEL SECURITY;
    ALTER TABLE public.auth_audit_log DISABLE ROW LEVEL SECURITY;
    ALTER TABLE public.scorer_feedback DISABLE ROW LEVEL SECURITY;
    GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
    ```
- [ ] **Step 2: Verify git status and commit documentation**
  - Commit: `docs(security): document supabase rls remediation and rollback plan`
