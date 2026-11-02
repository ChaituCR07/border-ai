# ADR 0029 — Notification Architecture: Outbox Pattern, Advisory Lock, and Concurrent Workers

## Status
Accepted

## Context
Threat alerts detected by the AI intelligence engine must reach external recipients (control room operators, area supervisors, duty officers) via SMTP email. External mail relays and network conditions introduce variable latency, socket timeouts, TLS negotiation delays, and transient outages. 

If notifications were dispatched inline during alert ingestion or REST API requests:
1. Video pipeline backpressure would stall real-time detection streams.
2. In-flight notification state would be lost upon server crashes.
3. Multi-instance server clusters would risk duplicate email dispatch or race conditions during escalation.

A resilient, scalable notification architecture is required that decouples delivery from core processing, ensures exactly-once planning, and guarantees non-blocking operation.

## Decisions

1. **Transactional Outbox Architecture:**
   - Notification dispatch is completely decoupled from alert generation using a dedicated database outbox table (`notifications`).
   - Alert ingestion writes alerts to PostgreSQL and broadcasts lightweight envelope events over Redis streams.
   - The notification lifecycle consists of two independent, asynchronously executed phases:
     - **Planner:** Discovers unhandled alerts, evaluates routing and cooldown policies, and inserts planned notification rows.
     - **Worker:** Claims due notification rows, formats MIME payloads, and dispatches them via SMTP.

2. **Exactly-Once Planning via Marker Anti-Join:**
   - To avoid planning the same alert multiple times without modifying the read-heavy `alerts` table index structure, a dedicated marker table `notification_planned (alert_id, planned_at)` is used.
   - The planner queries alerts using an anti-join:
     ```sql
     SELECT a.* FROM alerts a
      WHERE NOT EXISTS (
        SELECT 1 FROM notification_planned np WHERE np.alert_id = a.alert_id
      )
      AND a.created_at >= now() - interval '3600 seconds'
      ORDER BY a.created_at ASC
      LIMIT 100;
     ```
   - When an alert is processed, the alert's initial notification rows (and any future scheduled escalation rows) are inserted alongside the `notification_planned` marker in a single atomic database transaction.

3. **Planner Leader Election via PostgreSQL Session Advisory Lock:**
   - To eliminate double-planning in multi-instance horizontal deployments, the planner must execute as a single active leader.
   - The active instance acquires a PostgreSQL session-level advisory lock using key `727001`:
     ```sql
     SELECT pg_try_advisory_lock(727001) AS ok;
     ```
   - If acquired, the instance runs as the active planner (ticking every 1.5s). Secondary instances remain in standby mode, periodically attempting lock acquisition. Upon leader termination or connection failure, the lock is automatically released by PostgreSQL.

4. **Concurrent Worker Lease Management (`FOR UPDATE SKIP LOCKED`):**
   - Notification workers run concurrently without coordination bottlenecks.
   - Workers claim batches of due rows using PostgreSQL row-level locks:
     ```sql
     UPDATE notifications n
        SET status = 'SENDING',
            locked_until = now() + interval '60 seconds',
            attempts = n.attempts + 1
      WHERE n.notification_id IN (
        SELECT notification_id FROM notifications
         WHERE (status = 'PENDING' AND next_attempt_at <= now() AND due_at <= now())
            OR (status = 'SENDING' AND locked_until < now())
         ORDER BY due_at, created_at
         FOR UPDATE SKIP LOCKED
         LIMIT $1
      )
      RETURNING *;
     ```
   - Leases expire after 60 seconds (`locked_until`), ensuring crash recovery if a worker dies mid-flight.

5. **Retry Backoff with Deterministic Delays:**
   - Transient SMTP errors (network drops, 4xx responses) trigger retry scheduling with exponential backoff:
     $$\text{delay} = \min(1800, 30 \times 2^{\text{attempt}-1})\text{ seconds}$$
   - Permanent errors (5xx, domain rejected, mailbox non-existent) immediately mark the notification `FAILED` without retrying.

6. **Mailpit Local / Staging Emulation:**
   - Local and development environments use `axllent/mailpit` (ports 1025 SMTP, 8025 Web UI) inside `docker-compose.yml` to capture, inspect, and verify MIME emails without transmitting messages across the internet.

## Consequences
- REST API and AI pipeline operations are strictly isolated from SMTP availability and latency.
- Single planner leadership prevents race conditions and duplicate planning across cluster nodes.
- Horizontal worker scaling provides throughput scaling under alert spikes.
- Full delivery observability is preserved in the database audit log.
