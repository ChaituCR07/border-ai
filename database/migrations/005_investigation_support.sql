-- 005: Investigation support - plate normalisation, OCR look-alike key, trigram and forensic search indexes
BEGIN;

-- Trusted extension on PostgreSQL for trigram-based contains search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Plate normalisation: uppercase alphanumeric string stripped of spaces and punctuation
CREATE OR REPLACE FUNCTION plate_norm(t text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS
$$ SELECT regexp_replace(upper(coalesce(t,'')), '[^A-Z0-9]', '', 'g') $$;

-- OCR look-alike key mapping confusable character classes:
-- O, Q, D -> 0 | I -> 1 | B -> 8 | S -> 5 | Z -> 2 | G -> 6
CREATE OR REPLACE FUNCTION plate_key(t text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS
$$ SELECT translate(plate_norm(t), 'OQDIBSZG', '00018526') $$;

-- Generated columns on events table for zero-overhead, always-consistent indexing
ALTER TABLE events ADD COLUMN IF NOT EXISTS plate_norm text
  GENERATED ALWAYS AS (NULLIF(plate_norm(COALESCE(plate_number, metadata->>'plate')), '')) STORED;

ALTER TABLE events ADD COLUMN IF NOT EXISTS plate_key text
  GENERATED ALWAYS AS (NULLIF(plate_key(COALESCE(plate_number, metadata->>'plate')), '')) STORED;

-- Person identifier index (plain expression index on metadata->>'person_id')
CREATE INDEX IF NOT EXISTS idx_events_person ON events ((metadata->>'person_id')) WHERE metadata ? 'person_id';

-- Forensic search indexes
CREATE INDEX IF NOT EXISTS idx_events_plate_norm ON events (plate_norm text_pattern_ops, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_events_plate_key  ON events (plate_key, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_events_plate_trgm ON events USING gin (plate_norm gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_events_score_ts   ON events (threat_score DESC, "timestamp" DESC, event_id DESC);

COMMIT;
