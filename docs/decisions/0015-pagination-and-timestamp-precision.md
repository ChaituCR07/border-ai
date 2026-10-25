# ADR 0015 — Keyset Cursor Pagination and Microsecond Timestamp Precision

## Status
Accepted

## Context
Border surveillance generates high-throughput event streams where new records are continuously appended. Frontend dashboards query and live-tail events. Traditional `OFFSET` / `LIMIT` pagination causes two critical failures in high-volume surveillance environments:
1. **Page Drift / Skips:** When new events are inserted while an operator is paging through results, `OFFSET` causes events to shift positions, resulting in duplicate or skipped records.
2. **Performance Degradation:** High offsets (`OFFSET 100000`) force PostgreSQL to scan and discard thousands of rows.
3. **Timestamp Precision Loss:** PostgreSQL `timestamptz` stores microsecond precision (`YYYY-MM-DD HH:mm:ss.ssssss+00`). The default JavaScript `Date` object truncates timestamps to milliseconds, which causes records sharing the same millisecond to be skipped or duplicated during pagination.

## Decision
1. **Keyset (Cursor) Pagination:**
   - Pagination across `/api/events` and `/api/alerts` uses keyset pagination on the tuple `(timestamp DESC, event_id DESC)` (or `(created_at DESC, alert_id DESC)`).
   - Queries fetch `limit + 1` rows to determine `has_more`.
   - The pagination cursor encodes `{ t: string, id: string }` as a URL-safe base64 string (`base64url`).
   - The query condition applies:
     ```sql
     WHERE (timestamp, event_id) < ($1::timestamptz, $2::text)
     ```
2. **Lossless Type Parsers:**
   - The Node.js `pg` driver is configured with custom type parsers for `timestamptz` (OID 1184), `timestamp` (OID 1114), and `int8`/`bigint` (OID 20) to return raw strings instead of converting to native JavaScript `Date` or `Number`.
   - All timestamps travel across the REST API as ISO-8601 UTC strings with full microsecond precision (`YYYY-MM-DDTHH:mm:ss.ssssssZ`).

## Consequences
- **Positive:**
  - Keyset pagination is $O(1)$ relative to table size when supported by composite indexes `(timestamp DESC, event_id DESC)`.
  - Zero duplicate or skipped records during live surveillance feeds.
  - Microsecond precision preserved without loss.
- **Negative:**
  - Operators cannot jump to arbitrary page numbers (e.g., "Jump to page 42"), which is standard and expected for live event feeds.
