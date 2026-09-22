-- Phase 3: preserve the time each scorer was assigned a startup.
-- Existing assignments intentionally remain NULL because their historic
-- assignment time was not recorded before this migration.
ALTER TABLE judge_assignments
  ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ;

COMMENT ON COLUMN judge_assignments.assigned_at IS
  'Timestamp when this judge/startup assignment was created. NULL means the assignment predates timestamp tracking.';
