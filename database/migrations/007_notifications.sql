-- Migration 007: Notification Outbox, Exactly-Once Planning Marker, and Alert Resolution Lifecycle
BEGIN;

-- Alert lifecycle extensions
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolved_at      timestamptz;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolved_by      text;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolution       text;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolution_note  text;
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_resolution_chk;
ALTER TABLE alerts ADD CONSTRAINT alerts_resolution_chk
  CHECK (resolution IS NULL OR resolution IN ('TRUE_POSITIVE','FALSE_POSITIVE','DUPLICATE','OTHER'));
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS supersedes_alert_id text;

-- Exactly-once planning marker table
CREATE TABLE IF NOT EXISTS notification_planned (
  alert_id    text PRIMARY KEY,
  planned_at  timestamptz NOT NULL DEFAULT now(),
  outcome     text NOT NULL CHECK (outcome IN ('ROUTED','NO_ROUTE','STALE')),
  routes      integer NOT NULL DEFAULT 0
);

-- Notification outbox table
CREATE TABLE IF NOT EXISTS notifications (
  notification_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id        text NOT NULL,
  kind            text NOT NULL CHECK (kind IN ('ALERT','ESCALATION','DIGEST','TEST')),
  channel         text NOT NULL DEFAULT 'email',
  route_name      text NOT NULL,
  recipient       text NOT NULL,
  priority        text NOT NULL,
  group_key       text,
  status          text NOT NULL CHECK (status IN ('PENDING','SENDING','SENT','FAILED','CANCELLED','SKIPPED','DRY_RUN')),
  skip_reason     text,
  dedupe_key      text NOT NULL UNIQUE,
  due_at          timestamptz NOT NULL DEFAULT now(),
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  attempts        integer NOT NULL DEFAULT 0,
  locked_until    timestamptz,
  last_error      text,
  message_id      text,
  sent_at         timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- Fast lookup indexes for outbox claiming, deduplication and reporting
CREATE INDEX IF NOT EXISTS idx_notifications_due   ON notifications (next_attempt_at, due_at) WHERE status IN ('PENDING','SENDING');
CREATE INDEX IF NOT EXISTS idx_notifications_alert ON notifications (alert_id);
CREATE INDEX IF NOT EXISTS idx_notifications_group ON notifications (route_name, group_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_sent  ON notifications (sent_at DESC) WHERE status = 'SENT';

COMMIT;
