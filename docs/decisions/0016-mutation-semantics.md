# ADR 0016 — API Mutation Semantics, Idempotency, and Biometric Boundaries

## Status
Accepted

## Context
Operators in a multi-terminal command center may simultaneously respond to threat alerts. Furthermore, privacy and regulatory requirements (ADR 0009) demand strict separation of biometrics from general REST APIs. Camera stream credentials must also never be exposed or accepted in cleartext over REST.

## Decision
1. **Atomic and Idempotent Alert Acknowledgement:**
   - Alert acknowledgement (`PATCH /api/alerts/:id/acknowledge`) uses an atomic SQL update:
     ```sql
     UPDATE alerts
        SET status = 'ACKNOWLEDGED', acknowledged_by = $2, acknowledged_at = now(), updated_at = now()
      WHERE alert_id = $1 AND status IN ('NEW', 'OPEN')
     RETURNING *;
     ```
   - If 1 row is returned, the transition succeeds, and an immutable audit entry (`ALERT_ACK`) is written to `api_audit_log`.
   - If 0 rows are returned:
     - If the alert does not exist, `404 NOT_FOUND` is returned.
     - If the alert is already `ACKNOWLEDGED` or `RESOLVED`, the current record is returned with `200 OK`. The original `acknowledged_by` and `acknowledged_at` are preserved without mutation, and no duplicate audit log is recorded.
   - Concurrent requests from multiple operators result in exactly one winner and consistent `200 OK` responses across all clients.

2. **Watchlist Soft Deletion:**
   - `DELETE /api/watchlist/:id` sets `active = false` and stamps `deleted_at = now()`. Records are never physically deleted to preserve historical alert provenance and audit trails.
   - Deleting an already deleted record is idempotent and returns `204 No Content`.

3. **Strictly Non-Biometric REST Boundary:**
   - In accordance with ADR 0009, biometric face embeddings and images are enrolled exclusively through the specialized Python offline tool.
   - The watchlist REST API rejects any request body containing `embedding`, `image`, `face`, or `photo` properties with `400 VALIDATION_ERROR`.
   - `PERSON` entries require an explicit, non-empty `consent_reference` (e.g. `CONSENT-2026-001`). Omission triggers `400 VALIDATION_ERROR` (`CONSENT_REQUIRED`).

4. **Credential-Free Camera URLs:**
   - Camera `stream_url` is validated to prohibit embedded user credentials (`://user:pass@`). Violations are rejected with `400 VALIDATION_ERROR` (`CREDENTIALS_IN_URL`).
   - Credentials are referenced indirectly by name via `credentials_ref` and resolved securely by ingestion services.

## Consequences
- **Positive:**
  - Multi-operator race conditions in command centers are resolved safely.
  - Complete compliance with biometric consent and privacy architecture.
  - RTSP credentials cannot leak via API inspection or frontend network traffic.
- **Negative:**
  - Soft-deleted entries require filtered queries (`deleted_at IS NULL AND active = true`).
