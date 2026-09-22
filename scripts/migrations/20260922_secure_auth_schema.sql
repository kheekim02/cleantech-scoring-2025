-- Phase 3.5 authentication schema. Password hashes are populated by the paired
-- Node migration because PostgreSQL cannot create the application's scrypt hashes.
ALTER TABLE admins ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE judges ADD COLUMN IF NOT EXISTS password_hash TEXT;
-- New accounts use password_hash only. Existing plaintext passcodes remain
-- temporarily for rollback compatibility until the session rollout is verified.
ALTER TABLE admins ALTER COLUMN passcode DROP NOT NULL;
ALTER TABLE judges ALTER COLUMN passcode DROP NOT NULL;

CREATE TABLE IF NOT EXISTS auth_sessions (
  session_token TEXT PRIMARY KEY,
  role TEXT NOT NULL CHECK (role IN ('admin', 'scorer')),
  principal_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS auth_sessions_active_lookup_idx
  ON auth_sessions (role, principal_id, expires_at)
  WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS auth_audit_log (
  audit_id BIGSERIAL PRIMARY KEY,
  role TEXT NOT NULL CHECK (role IN ('admin', 'scorer')),
  principal_id TEXT NOT NULL,
  action TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
