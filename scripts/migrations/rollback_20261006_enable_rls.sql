-- CleanTech Open 2025 Diligence Engine
-- Rollback Migration for 20261006_enable_rls_and_revoke_public.sql
-- Date: 2026-10-06

BEGIN;

-- 1. Disable Row Level Security on the 6 tables that previously had it disabled
ALTER TABLE IF EXISTS public.startup_extractions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.judge_assignments DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.admins DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.auth_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.auth_audit_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.scorer_feedback DISABLE ROW LEVEL SECURITY;

-- Note: public.judges and public.human_reviews remain ENABLED because they had RLS enabled prior to this migration.

-- 2. Restore default privileges if required
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO anon, authenticated;

COMMIT;
