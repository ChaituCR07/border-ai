# ADR 0034: Reconciliation as the Correctness Oracle (Zero Loss Definition)

## Status
Accepted

## Context
Across a distributed video intelligence architecture involving an inference engine, local append-only journals, Redis streams, PostgreSQL, WebSocket gateways, and SMTP mail dispatch, each subsystem independently claims resilience. Proving systemic correctness requires a global reconciliation oracle that audits all storage surfaces after runs and chaos events.

## Decision

### 1. Invariants of "Zero Loss"
For any scenario execution window `[t0, t1]` after quiescence (settle period <= 60s):

1. **R01 (Journal Completeness):** Every event recorded in the engine's local append-only journal (`events.jsonl`) must exist in PostgreSQL (same `event_id`) OR in the Redis dead-letter stream (`surveillance.dead`) with an explicit error reason.
2. **R02 (No Phantom Events):** PostgreSQL contains no events absent from the engine journal.
3. **R03 (Duplicate Freedom):** `event_id` and `alert_id` are unique; neither the journal nor the database contains duplicate IDs.
4. **R04 (Alert Origin):** Every Redis alert has exactly one corresponding row in `alerts`.
5. **R05 (Notification Completeness):** Every alert with `priority = 'CRITICAL'` has at least one associated `notifications` row (`SENT`, `SKIPPED`, or `DRY_RUN`).
6. **R06 (Delivery Audit):** Every `SENT` notification has a matching `Message-ID` in the Mailpit inbox.
7. **R07 (Timestamp Monotonicity):** Per-camera event timestamps are monotonically non-decreasing (within 1.0s frame jitter tolerance) and never in the future (> now + 5.0s).
8. **R08 (Snapshot Integrity):** Every alert referencing a `snapshot_path` has an existing, readable JPEG on disk.

### 2. Documented Boundaries
- ByteTrack in-memory tracker state is not preserved across engine restarts; an ongoing incident may raise a new alert after restart.
- Email delivery provides at-least-once semantics during SMTP server reconnects.
- Authoritative record is the disk journal; un-flushed in-flight RAM events at the instant of a hard `kill -9` are not guaranteed.

## Consequences
- The automated reconciliation tool (`scripts/reconcile.py`) runs after every scenario and chaos test, exiting non-zero if any invariant is violated.
