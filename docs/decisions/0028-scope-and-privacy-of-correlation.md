# ADR 0028 — Privacy Scopes, Sequence Search Governance, and Caching

## Status
Accepted

## Context
Cross-camera correlation and multi-camera pattern searches can trace vehicular movement across broad regions. Left ungoverned, pattern search could be abused for untargeted mass surveillance or dragnet queries. Clear scope boundaries, role gating, mandatory purpose logging, and caching rules are required.

## Decisions

1. **Single-Subject Journey Scope:**
   - Single-subject journeys (`GET /api/investigation/journey` by `plate` or `vehicle_id`) are accessible to **Operator**, **Investigator**, and **Admin** roles.
   - **Viewer** role is strictly forbidden (`HTTP 403`).
   - Every execution records a `JOURNEY` entry to `api_audit_log` detailing user, query, row count, and `topology_version`.
   - An optional `end_at` parameter filters out events after a given timestamp, enabling alert drawers to display "Journey so far" up to the moment of the alert without forward information leakage.

2. **Multi-Camera Sequence Search Governance:**
   - Multi-camera sequence search (`GET /api/correlation/sequence`) identifies all vehicles matching an ordered sequence of 2 to 5 camera checkpoints.
   - **Restricted Access:** Allowed for **Investigator** and **Admin** roles only. Operators and Viewers are rejected with `HTTP 403`.
   - **Mandatory Operational Purpose:** Every sequence query requires an explicit `purpose` parameter with $\ge 5$ characters explaining the legal or operational justification (e.g., *"Operation Nightfall lead follow-up"*). Missing or short purpose returns `HTTP 422`.
   - **Search Limits:** Time span is capped at 7 days; results are capped at 50 plate clusters (`limit <= 50`).
   - **Audit Trail:** Every query is logged under action `SEQUENCE_SEARCH` with camera sequence, time window, max hop gap, purpose, and result counts.
   - **SQL Injection Defense:** Camera identifiers are validated against `^[A-Za-z0-9_-]{2,32}$` and bound as parameters in SQL CTE queries.

3. **In-Memory Caching with Unconditional Auditing:**
   - `GET /api/investigation/journey` results are cached in an in-memory LRU cache for 30 seconds.
   - Cache key includes: `(subject, from, to, end_at, correlate, topology_version, config_version)`.
   - Modifying topology or correlation configuration immediately invalidates the cache.
   - **Critical Privacy Invariant:** Cache hits still trigger unconditional audit log writes. Caching accelerates repeated forensic inspection without diminishing surveillance accountability.

4. **Event Drawer "Journey So Far":**
   - The alert/event drawer lazy-loads a compact strip with `end_at = event.timestamp`.
   - Network or correlation errors fail silently without blocking event details or drawer interactions.

## Consequences
- Dragnet mass surveillance is blocked by role gating, tight limits, and mandatory purpose declarations.
- Complete accountability is guaranteed across every query.
- System performance remains sub-300ms via safe in-memory caching.

