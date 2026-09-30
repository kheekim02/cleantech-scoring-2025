-- Lookup index for scorer hydration and admin progress aggregation.
-- Optimizes: WHERE startup_id = $1 AND judge_id = $2 (get-startup, admin-data).
-- Apply against the live Supabase database once:
--   psql "$DATABASE_URL" -f scripts/migrations/20260930_human_reviews_lookup_index.sql

CREATE INDEX IF NOT EXISTS idx_human_reviews_startup_judge
  ON human_reviews (startup_id, judge_id);
