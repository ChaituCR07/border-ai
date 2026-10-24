# 0013. Core Database Schema, Entity Semantics, and Persistence Architecture

**Date:** 2026-10-24  
**Status:** Accepted  
**Deciders:** Core Engineering Team  
**Consulted:** Data Architecture & Surveillance Operations Stakeholders  

---

## Context

In Day 13, we implemented an asynchronous, resilient event bus backed by Redis Streams (`surveillance.events`, `surveillance.alerts`, `surveillance.events.dead`). To support operational intelligence, analytical reporting, and the upcoming Day 15 REST API / Day 17 Investigation Dashboard, events must be durably persisted with query-optimized indexing and workflow state management.

Day 14 implements the core PostgreSQL relational schema (`cameras`, `events`, `alerts`, `alert_history`, `vehicles`, `detections`) along with an idempotent `PostgresEventSink` consuming from the Day 13 streaming processor.

---

## Decisions

### 1. Idempotency is a Hard Database Guarantee
`events.event_id` serves as the primary key. Ingestion writes utilize `INSERT INTO events ... ON CONFLICT (event_id) DO NOTHING`. Derived tables (`alerts`, `vehicles`, `detections`) enforce `UNIQUE (event_id)`. Re-delivered stream envelopes, journal replays, or crash redeliveries result in a no-op at the storage layer without duplicate side-effects.

### 2. Single Atomic Transaction Per Event
An incoming event envelope and all its derived entity rows (e.g. an alert row, vehicle sighting, or track summary) are written within a single atomic database transaction. Partial states (such as an event stored without its associated alert) are structurally impossible.

### 3. Detections Are Track Summaries, Not Per-Frame Telemetry
Recording high-rate bounding boxes across multiple 30 FPS cameras would saturate storage I/O and disk capacity with unindexed noise. Instead, the pipeline emits a `TRACK_SUMMARY` event when a track terminates (or flushes on stream finish), storing one summary row per object: classification, highest confidence, duration, frame hits, and bounding box coordinates. Flickering noise (< 5 hits) is filtered out.

### 4. Unknown Cameras Are Registered, Not Rejected
`events.camera_id` references `cameras (camera_id)`. To prevent event loss when a new or misconfigured camera node begins publishing before configuration seeding, the sink registers a placeholder camera with status `UNREGISTERED` within the same transaction. The operational dashboard alerts operators to unseeded hardware without dropping evidence.

### 5. Strict Error Classification (Permanent vs. Transient)
Database exceptions are explicitly classified:
- **Permanent Errors (`MappingError`, `InvalidRecord`):** Malformed timestamps, missing alert IDs, or invalid constraints cannot be fixed by retrying. They are immediately routed to `surveillance.events.dead` with reason metadata.
- **Transient Errors (`RepoUnavailable`):** Connection pool exhaustion or PostgreSQL downtime leaves messages in the Pending Entries List (PEL) to be reclaimed and retried on recovery.

### 6. Tolerant Severity vs. Strict Identity
An unrecognized severity label falls back to `NULL` (preserving the raw text in JSONB `metadata`). However, identity fields (`event_id`, `camera_id`, `timestamp`, and `alert_id` for threat alerts) are strictly validated up front.

### 7. Explicit Alert Denormalization
The `alerts` table duplicates `camera_id`, `threat_score`, `entity`, and `summary` from the event record. This enables sub-millisecond alert list queries, status filtering, and counter aggregations without requiring joins or dynamic JSON parsing.

### 8. Audited Human Decisions (`alert_history`)
Every alert status transition records the actor, previous status, next status, note, and timestamp in `alert_history`. In accordance with border security standards, alerts past `NEW` require an identified human operator (`CHECK (status = 'NEW' OR acknowledged_by IS NOT NULL)`).

### 9. Event Time vs. Storage Time
`events.timestamp` and `alerts.created_at` reflect the wall-clock or simulated video time when the event physically occurred. `received_at` logs when PostgreSQL inserted the row. Historical journal replays preserve original temporal integrity.

### 10. Explicit Data Retention & Lifecycle
Data lifecycle is managed via policy-driven retention (`scripts/db_retention.py`). Standard events and telemetry expire after a configured window (e.g., 30 days), while alerts are preserved longer (e.g., 365 days). Associated video snapshot files in `outputs/runs/` are retained alongside alert records.

### 11. Plain Schema Over Early Partitioning
The initial schema uses standard B-tree indexes and partial indexes on high-cardinality search columns (`timestamp DESC`, `camera_id`, `event_type`, `severity`, `plate_number`). Declarative time-partitioning is documented as a future migration path once event volumes warrant it.

### 12. Credentials Never Enter Database Tables
RTSP stream URLs containing credentials (`rtsp://user:pass@host/`) are stripped before storage in `cameras.rtsp_url`. A database check constraint enforces `CHECK (rtsp_url IS NULL OR rtsp_url !~ '://[^/@]+@')`. Credentials remain strictly in local environment variables.
