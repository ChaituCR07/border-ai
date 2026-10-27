# ADR 0020 — Real-Time WebSocket Gateway and Resynchronization Architecture

## Status
Accepted

## Context
Operators require sub-second notification of critical perimeter threats without periodic page refreshes or polling lag. However, network interruptions, laptop sleep cycles, and intermittent gateway or database restarts occur in production. A fragile real-time system that attempts to build full distributed at-least-once stateful messaging on top of WebSockets introduces complex sequence buffering, state drift, and split-brain failures.

## Decisions

1. **WebSocket as an Ephemeral Notification Channel; PostgreSQL as Source of Truth:**
   - Real-time WebSocket delivery is strictly **at-most-once**.
   - Absolute correctness is guaranteed through **REST resynchronization** (`GET /api/alerts?status=OPEN`) triggered upon connection establishment, reconnects, sequence gaps, or server epoch resets.
   - This eliminates the need for heavyweight server-side message spooling or per-client persistent replay logs.

2. **Stream Tail Consumer via Plain `XREAD BLOCK`, Not a Consumer Group:**
   - The WebSocket gateway consumes `surveillance.alerts` using plain `XREAD BLOCK` starting at `$` (new entries only).
   - In a multi-client or multi-gateway deployment, every gateway process must observe every alert to broadcast to its connected subscribers. A consumer group would load-balance messages across gateway instances, causing clients to miss alerts.
   - Avoids pending-entry list (PEL) bookkeeping and acknowledgement overhead for an ephemeral delivery channel.

3. **Database Hydration with Bounded Retry and Fallback:**
   - For every stream envelope received, the hydrator attempts to load the rich alert view from PostgreSQL using a bounded exponential backoff schedule: `[0, 50, 100, 200, 400, 800, 1500] ms`.
   - If PostgreSQL persistence lags or the sink is temporarily down, the gateway **still broadcasts** the alert reconstructed from envelope payload fields with `persisted: false`.
   - Edge independence: an operator never misses a live CRITICAL alert because the storage sink is queueing. The frontend renders the alert card immediately and disables the `[ACKNOWLEDGE]` button until a subsequent resync discovers the committed database record.

4. **Unified Data Transfer Object (DTO):**
   - The WebSocket `AlertView` schema matches the REST `AlertView` DTO exactly (with an added `persisted: boolean` flag), managed in the shared `@border-ai/protocol` package.

5. **Sequence Numbers and Server Epoch Tracking:**
   - Every state-changing message (`alert.created`, `alert.updated`, `resync_required`) increments a monotonic server sequence counter (`seq`).
   - A unique `server_epoch` (UUID/random identifier generated at process start) allows clients to detect gateway restarts.
   - App-level heartbeats (`type: 'heartbeat'`) carry the current `seq` every 15 seconds, allowing idle clients to immediately discover skipped messages and initiate resync.

6. **Single Gateway Instance for MVP with Documented Upgrade Path:**
   - Current deployment runs a single gateway process.
   - For horizontal scaling across multiple nodes:
     - Redis Pub/Sub for cross-node acknowledgement broadcast (`alert.updated`).
     - Global sequence coordination via Redis `INCR` or PostgreSQL `LISTEN/NOTIFY`.

## Consequences
- Clean separation between storage truth and delivery acceleration.
- Bounded memory footprint on the gateway.
- Resilience against database lag or temporary Redis stream consumer disconnection.
