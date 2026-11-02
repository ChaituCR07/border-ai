# ADR 0031 — Alert Lifecycle: Generation Invariants, Escalation Double-Safety, and Resolution

## Status
Accepted

## Context
Threat alerts are the primary operational artifacts of Border-AI. An alert progresses through multiple distinct lifecycle states: `OPEN` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `RESOLVED`. 

In previous development phases, subtle race conditions and timing gaps existed:
1. Snapshots were occasionally published to Redis streams before the underlying image had finished writing to disk.
2. Escalation notifications scheduled in the future could still fire if an operator acknowledged the alert shortly after worker row claiming.
3. Alert resolution lacked formal domain modeling, audit logging, and disposition recording.
4. Threat scoring thresholds were defined in disparate configuration files across Python and TypeScript, creating risk of scoring drift.

Strict generation invariants and lifecycle guarantees must be enforced.

## Decisions

1. **Snapshot-Before-Publish Guarantee:**
   - The AI engine must ensure evidence snapshots are fully and atomically persisted on disk before an alert is published to Redis streams.
   - The engine writes frame data to a temporary file (`.tmp.<uuid>`) in the target run directory and performs an atomic POSIX filesystem rename (`os.replace`) to the final snapshot path.
   - Only upon successful rename does the pipeline publish the alert envelope to Redis streams.
   - Subscribers reading the stream are guaranteed that any referenced `snapshot_path` exists immediately upon arrival.

2. **Single Source of Truth for Threat Thresholds:**
   - Threat scoring thresholds are unified into a single authoritative JSON file: `configs/threat_thresholds.json`.
   - Both the Python threat scoring engine (`ai-engine/app/threat/config.py`) and the TypeScript backend (`backend/src/config/thresholds.ts`) ingest this file.
   - Cross-language parity tests (`backend/tests/unit/threshold-parity.test.ts` and `ai-engine/tests/test_threshold_parity.py`) enforce identical priority classification across all scores (0–100) and edge cases.

3. **Double-Safety Escalation Cancellation (Invariant I5):**
   - When an alert is acknowledged (`POST /api/alerts/:id/ack`) or resolved (`PATCH /api/alerts/:id/resolve`), pending escalation notifications must be canceled.
   - To eliminate race conditions where a worker has already claimed an escalation notification right before acknowledgement commits, two independent defenses are applied:
     1. **Database Transaction Cancellation:** Inside the acknowledge/resolve transaction, pending escalation rows are updated:
        ```sql
        UPDATE notifications
           SET status = 'CANCELLED', skip_reason = 'acknowledged'
         WHERE alert_id = $1 AND kind = 'ESCALATION' AND status = 'PENDING';
        ```
     2. **Worker Pre-Send Verification:** Immediately prior to transmitting an `ESCALATION` email, the worker queries the alert status from the database:
        ```sql
        SELECT status FROM alerts WHERE alert_id = $1;
        ```
        If the status is not `OPEN`, the row is immediately marked `CANCELLED` and transmission is aborted.

4. **Alert Resolution Domain Lifecycle:**
   - Alerts can be resolved by Operator or Admin roles via `PATCH /api/alerts/:id/resolve`.
   - Resolution requires a valid disposition:
     - `FALSE_POSITIVE`: Benign detection or misclassification.
     - `VERIFIED_THREAT`: Confirmed security threat addressed by response units.
     - `RESOLVED_OTHER`: Routine checkpoint clearance or administrative closure.
   - An optional internal note (`resolution_note`, max 500 characters) may be attached.
   - Resolution transitions `status` to `RESOLVED`, sets `resolved_at = now()`, records `resolved_by = actor.id`, cancels pending escalations, and records an audit log entry in `api_audit_log`.

5. **Deep Link Navigation `/?alert=<id>`:**
   - Notification emails include authenticated deep links directly to `/?alert=<alert_id>`.
   - Opening the link automatically focuses the associated camera in the video grid and displays the evidence snapshot drawer.
   - If the alert was already acknowledged or resolved by another officer, an informational banner displays who handled the alert and when, preventing duplicate effort.

## Consequences
- Snapshot 404 race conditions are completely eliminated.
- Escalation notifications never fire after an alert has been acknowledged.
- Threat threshold drift between AI engine and backend REST API is prevented by automated cross-language CI tests.
- Complete operational auditability is maintained across the entire alert lifecycle.
