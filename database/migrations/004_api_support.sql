-- 004: API support tables, columns, and query indexes (Node.js REST API)
BEGIN;

-- Alerts: acknowledgement metadata + lifecycle
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS acknowledged_at timestamptz;
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_status_check;
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_status_chk;
ALTER TABLE alerts ADD CONSTRAINT alerts_status_chk
  CHECK (status IN ('NEW', 'OPEN', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED', 'FALSE_POSITIVE'));

-- Watchlist: soft delete + consent trace + notes
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS consent_reference text;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS notes text;

-- Cameras: credential indirection + display metadata
ALTER TABLE cameras ADD COLUMN IF NOT EXISTS credentials_ref text;
ALTER TABLE cameras ADD COLUMN IF NOT EXISTS location_label text;
ALTER TABLE cameras ADD COLUMN IF NOT EXISTS enabled boolean NOT NULL DEFAULT true;

-- API audit log for operational traceability
CREATE TABLE IF NOT EXISTS api_audit_log (
  audit_id    bigserial PRIMARY KEY,
  at          timestamptz NOT NULL DEFAULT now(),
  actor       text NOT NULL,
  action      text NOT NULL,
  entity_type text NOT NULL,
  entity_id   text NOT NULL,
  request_id  text,
  detail      jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_api_audit_log_at ON api_audit_log (at DESC);
CREATE INDEX IF NOT EXISTS idx_api_audit_log_entity ON api_audit_log (entity_type, entity_id);

-- Performance Indexes for Day 15 API Queries
CREATE INDEX IF NOT EXISTS idx_events_ts_id        ON events (timestamp DESC, event_id DESC);
CREATE INDEX IF NOT EXISTS idx_events_cam_ts       ON events (camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_sev_ts       ON events (severity, timestamp DESC) WHERE severity IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_type_ts      ON events (event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_open_prio    ON alerts (priority, created_at DESC) WHERE status IN ('NEW', 'OPEN');
CREATE INDEX IF NOT EXISTS idx_alerts_created      ON alerts (created_at DESC, alert_id DESC);
CREATE INDEX IF NOT EXISTS idx_watchlist_active    ON watchlist (entity_type) WHERE deleted_at IS NULL AND active;

COMMIT;
