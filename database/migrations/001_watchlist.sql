-- Watchlist core (Day 9). Column names follow the plan's Day 14 table, plus `description` from Day 9.

CREATE TABLE IF NOT EXISTS watchlist (
    watchlist_id          BIGSERIAL PRIMARY KEY,
    entity_type           TEXT NOT NULL CHECK (entity_type IN ('VEHICLE', 'PLATE', 'PERSON', 'FACE')),
    identifier            TEXT NOT NULL,                 -- as entered (plate text, person reference, face label)
    normalized_identifier TEXT NOT NULL,                 -- form used for matching (same rules as ANPR output)
    name                  TEXT NOT NULL,
    description           TEXT NOT NULL DEFAULT '',
    risk_level            TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    embedding             BYTEA,                         -- face embedding (Day 10); NULL for plates and vehicles
    active                BOOLEAN NOT NULL DEFAULT TRUE,
    created_by            TEXT NOT NULL DEFAULT 'system',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One ACTIVE entry per (type, normalized identifier); deactivated entries free the identifier.
CREATE UNIQUE INDEX IF NOT EXISTS watchlist_active_identifier_uq
    ON watchlist (entity_type, normalized_identifier) WHERE active;

-- Candidate fetch for near matches (same length).
CREATE INDEX IF NOT EXISTS watchlist_active_len_idx
    ON watchlist (char_length(normalized_identifier)) WHERE active;

CREATE TABLE IF NOT EXISTS watchlist_audit (
    audit_id     BIGSERIAL PRIMARY KEY,
    watchlist_id BIGINT,
    action       TEXT NOT NULL CHECK (action IN ('ADD', 'UPDATE', 'DEACTIVATE', 'RESTORE', 'IMPORT')),
    actor        TEXT NOT NULL,
    details      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watchlist_hits (
    hit_id           BIGSERIAL PRIMARY KEY,
    watchlist_id     BIGINT NOT NULL REFERENCES watchlist (watchlist_id),
    camera_id        TEXT NOT NULL,
    track_id         BIGINT NOT NULL,
    plate            TEXT NOT NULL,                       -- plate as recognized
    match_type       TEXT NOT NULL CHECK (match_type IN ('exact', 'near')),
    distance         REAL NOT NULL DEFAULT 0,
    plate_confidence REAL NOT NULL,
    score            INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    status           TEXT NOT NULL CHECK (status IN ('alert', 'review', 'suppressed')),
    event_id         TEXT,
    seen_at          TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS watchlist_hits_entry_idx ON watchlist_hits (watchlist_id, seen_at DESC);
CREATE INDEX IF NOT EXISTS watchlist_hits_seen_idx ON watchlist_hits (seen_at DESC);
