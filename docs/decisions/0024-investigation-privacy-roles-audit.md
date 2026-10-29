# ADR 0024 — Forensic Search Privacy Guardrails, Role Gating, and Audit Logging

## Status
Accepted

## Context
Forensic investigation tools provide capabilities to trace vehicle journeys, inspect event contexts, query person identifiers, and export bulk data. Unrestricted access to these tools presents severe surveillance and privacy risks. Guardrails, role gating, purpose tracking, and audit logging must be enforced at the API gateway layer.

## Decisions

1. **Role Gating Hierarchy:**
   - **OPERATOR:** Permitted to query event feeds, filter by camera, time, event type, and severity. Prohibited from person identifier searches, forensic CSV exports, and person-based journey correlation.
   - **INVESTIGATOR / ADMIN:** Permitted to perform forensic searches on plates, vehicles, and person identifiers; view vehicle journey strips; and export bulk event CSVs.

2. **Person Identifier Purpose Requirement:**
   - In adherence with national privacy frameworks and ADR 0009, querying events by `person_id` requires:
     - User role `INVESTIGATOR` or `ADMIN`.
     - An explicit `purpose` parameter with a minimum length of 5 characters.
   - Requests missing a valid purpose return HTTP 422 Unprocessable Entity with error code `PURPOSE_REQUIRED`.
   - Person-based journeys are explicitly **not offered** to prevent unconstitutional automated movement profiling.

3. **Mandatory Audit Logging for Sensitive Queries:**
   - Every sensitive query is recorded to `api_audit_log`:
     - Queries specifying `plate`, `vehicle_id`, or `person_id` in `GET /api/events`.
     - All invocations of `GET /api/investigation/journey`.
     - All invocations of `GET /api/investigation/export.csv`.
   - Log schema: `actor`, `action`, `entity_type`, `entity_id`, `request_id`, `detail: { actor_role, endpoint, query_json, purpose, row_count, ip }`.
   - Writes to `api_audit_log` are fire-and-forget in the response lifecycle so auditing does not degrade search latency.

4. **CSV Export Injection Defense and Streaming Protection:**
   - Export endpoint `GET /api/investigation/export.csv` streams UTF-8 CSV data.
   - All cell values are processed through `csvCell()`. If a string begins with formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`), a single quote (`'`) is prepended to neutralize spreadsheet formula execution (CSV injection / DDE attacks).
   - Hard cap of 10,000 rows per export. Queries exceeding 10,000 rows append `# TRUNCATED: Export capped at 10000 rows. Narrow your filters.`

## Consequences
- Full accountability for sensitive queries through an immutable audit trail.
- Defense-in-depth protection against spreadsheet client vulnerabilities.
- Operators cannot execute bulk data extraction or person profiling without supervisor authorization.
