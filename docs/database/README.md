# Border-AI Database Schema & Migration Guide

This document catalogs the PostgreSQL 16 relational core schema, domain table groups, data ownership boundaries, and migration chronology for the Border-AI Video Intelligence Platform.

---

## 1. Domain Table Grouping

The database schema is partitioned into five functional domains:

### Domain A: Cameras & Spatial Topology
- **`cameras`**: Stores registered video streams, RTSP URLs, enabled model manifests, operational status, and heartbeat timestamps.
- **`zones`**: Polygonal boundaries (`restricted`, `buffer`, `transit`) defined in normalized coordinates $[0.0, 1.0]$.
- **`lines`**: Directional tripwires with crossing vector definitions.
- **`camera_topology`**: Inter-camera adjacency matrix, expected transition transit times, and anomaly speed thresholds.

### Domain B: Events, Tracks & Sightings
- **`events`**: High-frequency spatial, behavioural, and system events. Indexed on `(timestamp DESC, event_id DESC)` for $O(1)$ keyset cursor pagination (ADR 0015).
- **`track_summaries`**: Aggregated track life summaries (trajectory, dwell time, object class, license plate) providing a **99.5% storage volume reduction** over raw per-frame bounding boxes.
- **`vehicle_sightings`**: Normalized plate appearance logs with OCR confidence and visual attributes.

### Domain C: Alerts & Notification Outbox
- **`alerts`**: High-priority threat scoring incidents with UUID primary keys, 4-tier severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), composite score (0–100), explainable factor breakdown (`contributions`), and snapshot evidence file paths.
- **`notification_outbox`**: Transactional outbox table guaranteeing reliable, at-least-once SMTP email notification dispatch without distributed locks (ADR 0029).

### Domain D: Watchlists & Identity Intelligence
- **`watchlist_vehicles`**: Curated vehicle database with normalized plate index (`plate_norm`), severity, and notes.
- **`watchlist_hits`**: Correlated sighting records with OCR-aware look-alike phonetic substitution scoring.
- **`face_watchlist` & `face_sightings`**: Consent-gated prototype face recognition tables (disabled by default; stores 128-d L2 normalized vectors).

### Domain E: Security, RBAC & Immutable Audit Log
- **`users`**: Administrative and operator accounts with Argon2id password hashes and role designations (`VIEWER`, `OPERATOR`, `INVESTIGATOR`, `ADMIN`).
- **`sessions`**: Active authentication sessions with rotating refresh token hashes.
- **`api_audit_log`**: Immutable, append-only operational audit trail verified via a cryptographic SHA-256 hash chain (`prev_hash` $\to$ `current_hash`).

---

## 2. Table Ownership Rules (ADR 0014)

To prevent split-brain concurrency and maintain relational integrity:
- **Python AI Engine (`border_engine` role):** Exclusively writes new records to `events`, `track_summaries`, `vehicle_sightings`, and `watchlist_hits`. Holds read-only access to `cameras`, `zones`, `lines`, and `watchlist_vehicles`. Holds **zero** access to `users` and `sessions`.
- **Node.js Fastify API (`border_backend` role):** Exclusively writes state transitions on `alerts` (`status = 'ACKNOWLEDGED'`), manages `cameras` and `watchlists`, and appends to `api_audit_log`.
- **Asynchronous Sink Worker (`border_sink` role):** Dedicated append-only service persisting streaming events from Redis Streams into PostgreSQL.

---

## 3. Migration Chronology (001 – 009)

| Migration | File | Description |
|---|---|---|
| **001** | `001_watchlist.sql` | Watchlist vehicles, normalized plate unique index, and hit correlation log |
| **002** | `002_face_embeddings.sql` | Consent-gated face biometric embeddings and sighting tables |
| **003** | `003_core_schema.sql` | Cameras, restricted zones, tripwires, events, detections, and alerts |
| **004** | `004_api_support.sql` | Keyset pagination indexes and initial audit logging support |
| **005** | `005_investigation_support.sql` | Track life summaries, forensic vehicle sightings, and facet indexes |
| **006** | `006_correlation_support.sql` | Inter-camera topology graph, transit bounds, and journey segments |
| **007** | `007_notifications.sql` | Transactional notification outbox and anti-join dispatch index |
| **008** | `008_alerts_received_at.sql` | Clock skew tolerance and microsecond timestamp resolution index |
| **009** | `009_auth_and_security.sql` | Argon2id users, rotating session tokens, and SHA-256 hash-chained audit log |
