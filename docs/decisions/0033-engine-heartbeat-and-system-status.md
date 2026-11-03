# ADR 0033: Engine Heartbeat & System Status Aggregation

## Status
Accepted

## Context
Operators and integration test harnesses require an authoritative source of truth for the health of the engine, database, stream buses, and camera streams. Previously, camera health was estimated purely in the client browser based on HLS/MJPEG element load errors, which fails to distinguish between network disconnections, server restarts, and frozen CCTV streams (where the TCP connection remains open but no new frames arrive).

## Decision

### 1. Redis Heartbeat with TTL Expiry
The AI engine runs an independent background daemon thread (`HeartbeatPublisher`) that periodically writes telemetry to Redis:
- Engine status: `engine:status` with `EX 15` (refreshed every 5s).
- Per-camera status: `camera:status:{camera_id}` with `EX 15`.
- **Inherent Expiry:** If a process crashes or is terminated, its key vanishes from Redis within 15 seconds. Absence of a key represents `OFFLINE`.

### 2. State Classification
Camera states are classified strictly into four operational states:
- `ONLINE`: Connected and recent frame processed within <= 10.0s.
- `STALLED`: Connection open but no new frame received for > 10.0s (e.g. frozen CCTV sensor).
- `RECONNECTING`: Socket closed, actively retrying connection with exponential backoff.
- `OFFLINE`: No connection, disabled, or missing heartbeat.

### 3. Non-Blocking Guarantee
The heartbeat thread catches and suppresses all network and Redis exceptions. Heartbeat publication failures can never block or crash inference or ingestion.

### 4. Backend `/api/system/status` Aggregation
Node backend exposes a unified endpoint aggregating Postgres, Redis, Engine, Sink lag, Gateway clients, and Camera statuses into an overall status: `OK | DEGRADED | DOWN`. Result is cached for 2s to protect databases from polling overload.

## Consequences
- Solves the silent stalled CCTV stream hazard.
- Provides identical health data to operators, dashboards, and automated chaos test harnesses.
