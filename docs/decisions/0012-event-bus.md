# 0012. Event Bus Architecture, Delivery Guarantees, and Stream Semantics

**Date:** 2026-10-22  
**Status:** Accepted  
**Deciders:** Core Engineering Team  
**Consulted:** Distributed Systems & Surveillance Operations Stakeholders  

---

## Context

In Day 12, we completed the Threat Scoring and Escalation Engine, generating real-time compound events and high-priority `THREAT_ALERT` messages. As the system scales toward multi-camera perimeter deployments, these events must be reliably propagated from edge video analytics nodes to downstream persistence (Day 14 PostgreSQL), real-time notification gateways (Day 17 WebSockets), and operational dashboards.

Direct database writes or synchronous network calls from the video pipeline introduce backpressure, latency spikes, and catastrophic failure modes if downstream services experience outages. Day 13 implements an asynchronous, reliable event pipeline using **Redis Streams** (`surveillance.events`, `surveillance.alerts`, `surveillance.events.dead`) and a decoupled **Event Processor** with consumer groups.

---

## Decisions

### 1. The Vision Pipeline Never Waits for Redis
Publishing from the computer vision pipeline is strictly an in-memory queue operation (`EventPublisher.publish()`). A dedicated background worker thread handles network communication, batching, and retries. If Redis is down, network partitions occur, or the broker is slow, frame ingestion, object detection, multi-camera tracking, rule evaluation, and threat scoring continue without interruption. Under no circumstances may Redis latency degrade inference FPS.

### 2. The Journal Stays the Primary Source of Truth
On edge camera nodes, the append-only JSONL journal (`events.jsonl` within the run directory) is written synchronously before an event is handed to the publisher. The event bus is a decoupled, best-effort delivery copy with automatic retry. Any events dropped due to extended network outages or process termination can be safely restored via the journal replay utility (`scripts/replay_journal.py`).

### 3. At-Least-Once Delivery with Idempotent Consumers
Redis Streams with consumer groups provide at-least-once delivery semantics. Network dropouts during batch submission or consumer restarts during execution can cause redeliveries. Consequently, every consumer and downstream sink must be **strictly idempotent** by `event_id`:
- The `EventProcessor` maintains a bounded in-memory cache of recently processed UUIDs (`dedupe_cache: 20000`).
- Downstream database sinks (Day 14) enforce idempotency at the storage engine level via `INSERT ... ON CONFLICT (event_id) DO NOTHING`.

### 4. One Versioned Envelope
Stream entries are serialized as flat string key-value pairs following schema version `v=1`. Top-level routing fields (`v`, `event_id`, `type`, `camera`, `ts`, `severity`, `run_id`) are maintained alongside a complete JSON string `data` field:
- Consumers can inspect metadata, filter by camera, or route by severity without deserializing the inner payload.
- Payload structures can evolve without breaking stream consumers.
- Envelopes with unrecognized schema versions (`v != 1`) or invalid fields are rejected directly into the dead-letter stream rather than guessed.

### 5. Precious Events Survive Outages Longer (Priority-Aware Buffering)
During network outages, the publisher buffers events in memory up to configurable limits. Two separate queues are maintained:
- `buffer_high` (default 5,000 entries) for high-priority events (`THREAT_ALERT`, `WATCHLIST_MATCH`, and security violations).
- `buffer_low` (default 20,000 entries) for high-volume observation telemetry (`ZONE_ENTER`, `ZONE_EXIT`, `LINE_CROSSING`).
When buffers fill during prolonged downtime, low-priority observations are shed first, preserving critical threat alerts. Global sequence numbers ensure strict order preservation when draining merged batches.

### 6. Poison Messages Do Not Block the Stream
Malformed messages (syntax errors, invalid schema versions, missing track IDs, or timestamp mismatches) are trapped immediately upon parsing and routed to `surveillance.events.dead` with an explicit reason code and origin ID. Messages that cause transient sink exceptions are left unacknowledged and reclaimed after `reclaim_idle_ms`. If a message repeatedly fails beyond `max_deliveries` (default 5), it is acknowledged and dead-lettered with the stack trace, preventing queue head-of-line blocking.

### 7. Acknowledge After Success Only
A stream entry is acknowledged via `XACK` only after **all** registered sinks have successfully processed the event. If a consumer crashes mid-handling, the unacknowledged entry remains in the Pending Entries List (PEL). A sibling consumer will reclaim the message after `reclaim_idle_ms` via `claim_stale` (`XAUTOCLAIM`), preventing event loss during container crashes.

### 8. Bounded Stream Length (MAXLEN ~)
All streams are bounded using approximate trimming (`MAXLEN ~ 100000` for main events, `10000` for alerts and dead-letter queues) to protect Redis memory. Consumer lag is continuously monitored via `stream_stats.py`. If a consumer falls so far behind that unread entries are trimmed, the run's local journal provides the canonical recovery path.

### 9. Privacy and Security Hardening
Video event metadata includes recognized license plate numbers, track trajectories, and camera locations. Redis instances must be bound to loopback interfaces (`127.0.0.1`) or secure internal subnets, secured with authentication (`requirepass`), and connection URLs containing passwords must be masked in all log outputs.

### 10. Stream Ordering Semantics
Ordering is guaranteed strictly within a single stream when consumed by a single worker. When scaling across multiple consumers within a single consumer group, message delivery order across workers is non-deterministic. Downstream sinks must never rely on stream arrival order, using the event's embedded ISO/epoch timestamp (`ts_ms`) for temporal sequencing.

---

## Consequences

### Positive
- Edge vision pipeline is completely decoupled from Redis availability and network latency.
- Zero event loss architecture through dual-layer persistence (local journal + stream buffering + journal replay).
- Resilient recovery against consumer crashes, poison payloads, and transient downstream failures.
- Dedicated alerts stream (`surveillance.alerts`) allows low-overhead real-time monitoring by WebSocket consumers without filtering high-volume telemetry.

### Negative / Trade-offs
- Downstream sinks must implement idempotency checks and handle out-of-order deliveries.
- Edge nodes require sufficient RAM to support publisher buffer queues (approx. 25 MB for 25,000 envelopes).
- In multi-consumer setups, stream delivery order is not strictly FIFO across workers.
