-- Migration 008: Add received_at column to alerts table
-- Decouples DB reception / insertion time from simulated or historical event time.
-- Used by notification planning, catch-up horizon, escalation and relative dashboard timers.

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_alerts_received_at ON alerts (received_at DESC);
