-- 003: core tables for the event pipeline (cameras, events, alerts, vehicles, detections)

-- ---------------------------------------------------------------- cameras
CREATE TABLE IF NOT EXISTS cameras (
    camera_id   TEXT PRIMARY KEY CHECK (camera_id ~ '^[A-Za-z0-9_.-]{1,64}$'),
    name        TEXT NOT NULL,
    location    TEXT NOT NULL DEFAULT '',
    rtsp_url    TEXT CHECK (rtsp_url IS NULL OR rtsp_url !~ '://[^/@]+@'),      -- never a credential
    status      TEXT NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'INACTIVE', 'OFFLINE', 'MAINTENANCE', 'UNREGISTERED')),
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- events
CREATE TABLE IF NOT EXISTS events (
    event_id      TEXT PRIMARY KEY CHECK (char_length(event_id) BETWEEN 1 AND 64),
    event_seq     BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,                    -- for the readable EVT_000123 reference
    camera_id     TEXT NOT NULL REFERENCES cameras (camera_id),
    event_type    TEXT NOT NULL CHECK (event_type ~ '^[A-Z][A-Z0-9_]{2,60}$'),
    track_id      BIGINT NOT NULL,
    severity      TEXT CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    threat_score  INTEGER CHECK (threat_score BETWEEN 0 AND 100),                -- set for THREAT_ALERT events
    timestamp     TIMESTAMPTZ NOT NULL,                                          -- event time, not storage time
    snapshot_path TEXT,                                                          -- relative to outputs/runs/
    plate_number  TEXT,
    object_class  TEXT,
    rule_id       TEXT,
    rule_kind     TEXT,
    run_id        TEXT NOT NULL DEFAULT '',
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,                            -- the complete event JSON
    received_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION event_ref(seq BIGINT) RETURNS TEXT
LANGUAGE sql IMMUTABLE AS $$ SELECT 'EVT_' || lpad(seq::text, 6, '0') $$;

CREATE INDEX IF NOT EXISTS idx_events_time        ON events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_camera_time ON events (camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_time   ON events (event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_severity    ON events (severity, timestamp DESC) WHERE severity IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_plate       ON events (plate_number, timestamp DESC) WHERE plate_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_track       ON events (camera_id, track_id);

-- ---------------------------------------------------------------- alerts
CREATE TABLE IF NOT EXISTS alerts (
    alert_id        TEXT PRIMARY KEY CHECK (char_length(alert_id) BETWEEN 1 AND 64),
    event_id        TEXT NOT NULL UNIQUE REFERENCES events (event_id) ON DELETE CASCADE,
    camera_id       TEXT NOT NULL REFERENCES cameras (camera_id),
    priority        TEXT NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    threat_score    INTEGER NOT NULL CHECK (threat_score BETWEEN 0 AND 100),
    status          TEXT NOT NULL DEFAULT 'NEW'
                    CHECK (status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED', 'FALSE_POSITIVE')),
    entity          TEXT NOT NULL DEFAULT '',                                    -- groups the escalations of one subject
    summary         TEXT NOT NULL DEFAULT '',
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL,                                        -- the alert's event time
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status = 'NEW' OR acknowledged_by IS NOT NULL)                        -- no anonymous decisions
);

CREATE INDEX IF NOT EXISTS idx_alerts_status_time   ON alerts (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_priority_time ON alerts (priority, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_camera_time   ON alerts (camera_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_entity        ON alerts (entity, created_at DESC) WHERE entity <> '';

CREATE TABLE IF NOT EXISTS alert_history (
    history_id  BIGSERIAL PRIMARY KEY,
    alert_id    TEXT NOT NULL REFERENCES alerts (alert_id) ON DELETE CASCADE,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    actor       TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_alert_history_alert ON alert_history (alert_id, history_id);

-- ---------------------------------------------------------------- vehicles (plate sightings)
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id    BIGSERIAL PRIMARY KEY,
    event_id      TEXT NOT NULL UNIQUE REFERENCES events (event_id) ON DELETE CASCADE,
    camera_id     TEXT NOT NULL REFERENCES cameras (camera_id),
    track_id      BIGINT NOT NULL,
    plate_number  TEXT NOT NULL,
    confidence    REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    timestamp     TIMESTAMPTZ NOT NULL,
    vehicle_class TEXT,
    final         BOOLEAN NOT NULL DEFAULT FALSE,
    plate_format  TEXT
);
CREATE INDEX IF NOT EXISTS idx_vehicles_plate_time  ON vehicles (plate_number, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vehicles_camera_time ON vehicles (camera_id, timestamp DESC);

-- ---------------------------------------------------------------- detections (one summary per tracked object)
CREATE TABLE IF NOT EXISTS detections (
    detection_id BIGSERIAL PRIMARY KEY,
    event_id     TEXT NOT NULL UNIQUE REFERENCES events (event_id) ON DELETE CASCADE,
    camera_id    TEXT NOT NULL REFERENCES cameras (camera_id),
    track_id     BIGINT NOT NULL,
    object_type  TEXT NOT NULL,
    confidence   REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    timestamp    TIMESTAMPTZ NOT NULL,                                           -- last seen
    first_seen   TIMESTAMPTZ NOT NULL,
    last_seen    TIMESTAMPTZ NOT NULL,
    duration_s   REAL NOT NULL CHECK (duration_s >= 0),
    hits         INTEGER NOT NULL CHECK (hits >= 0),
    bbox         JSONB                                                           -- [x1, y1, x2, y2] in frame pixels
);
CREATE INDEX IF NOT EXISTS idx_detections_camera_time ON detections (camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detections_type_time   ON detections (object_type, timestamp DESC);

-- ---------------------------------------------------------------- views for the dashboard
CREATE OR REPLACE VIEW vehicle_plates AS
SELECT plate_number,
       count(*)                      AS sightings,
       count(DISTINCT camera_id)     AS cameras,
       min(timestamp)                AS first_seen,
       max(timestamp)                AS last_seen,
       max(confidence)               AS best_confidence
FROM vehicles
GROUP BY plate_number;

CREATE OR REPLACE VIEW alert_counts AS
SELECT priority,
       count(*)                                                   AS total,
       count(*) FILTER (WHERE status = 'NEW')                     AS new_count,
       count(*) FILTER (WHERE status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS')) AS open_count
FROM alerts
GROUP BY priority;
