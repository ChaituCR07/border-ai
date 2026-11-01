-- 006: Correlation support - camera schematic coordinates, camera links topology, and sequence search index
BEGIN;

ALTER TABLE cameras ADD COLUMN IF NOT EXISTS map_x numeric(5,2);
ALTER TABLE cameras ADD COLUMN IF NOT EXISTS map_y numeric(5,2);

CREATE TABLE IF NOT EXISTS camera_links (
  link_id     bigserial PRIMARY KEY,
  camera_a    text NOT NULL REFERENCES cameras(camera_id),
  camera_b    text NOT NULL REFERENCES cameras(camera_id),
  min_s       integer NOT NULL CHECK (min_s >= 0),
  typical_s   integer NOT NULL,
  max_s       integer NOT NULL,
  direction   text NOT NULL DEFAULT 'both' CHECK (direction IN ('both', 'a_to_b')),
  overlap     boolean NOT NULL DEFAULT false,
  notes       text,
  updated_at  timestamptz NOT NULL DEFAULT now(),
  CHECK (min_s <= typical_s AND typical_s <= max_s),
  CHECK (camera_a <> camera_b),
  UNIQUE (camera_a, camera_b)
);

-- Sequence search index: tight range scan on (camera_id, plate_key, timestamp)
CREATE INDEX IF NOT EXISTS idx_events_cam_platekey_ts
  ON events (camera_id, plate_key, "timestamp") WHERE plate_key IS NOT NULL;

COMMIT;

