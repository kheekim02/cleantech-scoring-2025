-- CleanTech Open 2025 Diligence Engine
-- Security Migration: Enable Row Level Security (RLS) on public schema tables
-- and revoke unauthenticated PostgREST permissions from anon and authenticated roles.
-- Date: 2026-10-06

BEGIN;

-- 1. Enable Row Level Security across all public tables
ALTER TABLE IF EXISTS public.startup_extractions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.judge_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.auth_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.auth_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.scorer_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.judges ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.human_reviews ENABLE ROW LEVEL SECURITY;

-- 2. Revoke all privileges from anon and authenticated roles in public schema
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon, authenticated;

-- 3. Set default privileges to prevent auto-granting on future tables created in public
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON ROUTINES FROM anon, authenticated;

COMMIT;
