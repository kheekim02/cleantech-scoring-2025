-- Migration: Add is_test flag to judges table for test/preview accounts
-- Date: 2026-09-23

ALTER TABLE judges ADD COLUMN IF NOT EXISTS is_test BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN judges.is_test IS 'True if account is for testing/admin preview (views all companies, scores not logged to database)';

-- Seed initial test/preview account if not already created
-- Username: admin_preview, Password: preview2025
-- Hash: scrypt$439813ea0370b5d14bb8166762033b94$9fd8365825a310b0637f95180aab26633eecc4aa2d7b5f9bad72aebb964c046ca5c30bf08be8fd316a2d8ba85e89cd81e3169ec33bea979127cedf2ee97bc0ba
INSERT INTO judges (judge_id, passcode, password_hash, is_test)
VALUES (
  'admin_preview',
  'preview2025',
  'scrypt$439813ea0370b5d14bb8166762033b94$9fd8365825a310b0637f95180aab26633eecc4aa2d7b5f9bad72aebb964c046ca5c30bf08be8fd316a2d8ba85e89cd81e3169ec33bea979127cedf2ee97bc0ba',
  TRUE
)
ON CONFLICT (judge_id) DO UPDATE 
SET is_test = TRUE;
