-- Migration 009: Authentication, Sessions, Auth Throttle, Vault, Governance, and Tamper-Evident Audit Chain
BEGIN;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
  user_id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username             text NOT NULL,
  email                text,
  display_name         text,
  role                 text NOT NULL CHECK (role IN ('ADMIN', 'OPERATOR', 'INVESTIGATOR', 'VIEWER')),
  password_hash        text NOT NULL,                    -- PHC formatted string (Argon2id)
  password_history     jsonb NOT NULL DEFAULT '[]'::jsonb, -- Last 5 password hashes for reuse prevention
  status               text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'DISABLED')),
  must_change_password boolean NOT NULL DEFAULT false,
  token_version        integer NOT NULL DEFAULT 1,       -- Incremented to invalidate all access tokens
  failed_attempts      integer NOT NULL DEFAULT 0,
  last_failed_at       timestamptz,
  last_login_at        timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now(),
  created_by           uuid,
  updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower ON users (lower(username));
CREATE INDEX IF NOT EXISTS idx_users_role_status ON users (role, status);

-- 2. Sessions Table (Rotating Refresh Tokens)
CREATE TABLE IF NOT EXISTS sessions (
  session_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  family_id            uuid NOT NULL,                    -- All tokens in a rotation lineage share this family ID
  refresh_hash         text NOT NULL UNIQUE,             -- SHA-256 hash of the opaque refresh token
  issued_at            timestamptz NOT NULL DEFAULT now(),
  last_used_at         timestamptz NOT NULL DEFAULT now(),
  expires_at           timestamptz NOT NULL,             -- Sliding idle expiration
  absolute_expires_at  timestamptz NOT NULL,             -- Absolute session expiration (e.g. 12 hours)
  rotated_at           timestamptz,                      -- Timestamp when successor was issued
  replaced_by          uuid REFERENCES sessions(session_id) ON DELETE SET NULL,
  revoked_at           timestamptz,
  revoke_reason        text,                             -- LOGOUT | LOGOUT_ALL | REUSE | PASSWORD_CHANGE | ADMIN | DISABLED
  ip                   inet,
  user_agent_hash      text
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id, revoked_at);
CREATE INDEX IF NOT EXISTS idx_sessions_family ON sessions (family_id);
CREATE INDEX IF NOT EXISTS idx_sessions_refresh_hash ON sessions (refresh_hash);

-- 3. Auth Throttling & Brute-Force Rate Limiting Table
CREATE TABLE IF NOT EXISTS auth_throttle (
  key                  text PRIMARY KEY,                 -- 'acct:<lower(username)>' or 'ip:<addr>'
  failures             integer NOT NULL DEFAULT 0,
  window_start         timestamptz NOT NULL DEFAULT now(),
  blocked_until        timestamptz
);

-- 4. Extend API Audit Log for Role, IP, User Agent, and Hash Chaining
ALTER TABLE api_audit_log ADD COLUMN IF NOT EXISTS role text;
ALTER TABLE api_audit_log ADD COLUMN IF NOT EXISTS ip inet;
ALTER TABLE api_audit_log ADD COLUMN IF NOT EXISTS user_agent_hash text;
ALTER TABLE api_audit_log ADD COLUMN IF NOT EXISTS prev_hash text;
ALTER TABLE api_audit_log ADD COLUMN IF NOT EXISTS hash text;

CREATE INDEX IF NOT EXISTS idx_api_audit_log_hash ON api_audit_log (hash);

-- Audit Head Table (Maintains Tip Hash for Hash Chaining)
CREATE TABLE IF NOT EXISTS audit_head (
  head_id              integer PRIMARY KEY DEFAULT 1,
  hash                 text NOT NULL,
  updated_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT single_head CHECK (head_id = 1)
);

INSERT INTO audit_head (head_id, hash)
VALUES (1, '0000000000000000000000000000000000000000000000000000000000000000')
ON CONFLICT (head_id) DO NOTHING;

-- Trigger to Prevent UPDATE and DELETE on api_audit_log
CREATE OR REPLACE FUNCTION trg_prevent_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Audit log entries are immutable and cannot be updated or deleted';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_api_audit_log_immutable ON api_audit_log;
CREATE TRIGGER trg_api_audit_log_immutable
BEFORE UPDATE OR DELETE ON api_audit_log
FOR EACH ROW EXECUTE FUNCTION trg_prevent_audit_tampering();

-- 5. Camera Encrypted Credential Vault Table (AES-256-GCM)
CREATE TABLE IF NOT EXISTS camera_credentials (
  camera_id            text PRIMARY KEY REFERENCES cameras(camera_id) ON DELETE CASCADE,
  key_id               text NOT NULL,
  nonce                text NOT NULL,                    -- Base64 encoded 12-byte IV
  ct                   text NOT NULL,                    -- Base64 encoded ciphertext
  tag                  text NOT NULL,                    -- Base64 encoded 16-byte authentication tag
  updated_at           timestamptz NOT NULL DEFAULT now(),
  updated_by           uuid
);

-- 6. Config Governance Table (Versioned, Audited Configuration)
CREATE TABLE IF NOT EXISTS config_versions (
  config_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name                 text NOT NULL,
  version              integer NOT NULL,
  content              jsonb NOT NULL,
  sha256               text NOT NULL,
  created_by           uuid,
  created_at           timestamptz NOT NULL DEFAULT now(),
  reason               text NOT NULL,
  active               boolean NOT NULL DEFAULT true
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_config_versions_name_ver ON config_versions (name, version);
CREATE INDEX IF NOT EXISTS idx_config_versions_active ON config_versions (name) WHERE active;

COMMIT;
