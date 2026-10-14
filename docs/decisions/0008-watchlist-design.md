# Architecture Decision Record 0008: Watchlist System Design

- **Status:** Accepted
- **Date:** 2026-10-14
- **Branch:** feature/watchlist

## Context
Day 9 of the border surveillance system introduces a managed watchlist capable of storing `VEHICLE`, `PLATE`, `PERSON`, and `FACE` entities. Plate recognitions from the ANPR engine must trigger lookups, yielding structured `WATCHLIST_MATCH` events, track flags, and video overlay indications without degrading pipeline throughput or dropping critical alerts during transient database issues.

## Key Decisions

1. **PostgreSQL as Source of Truth with Real-Time Lookups:** Lookups query PostgreSQL directly so newly inserted or deactivated entries take effect on the very next recognized plate without cache invalidation delays. Exact lookups use an active partial index; near lookups query same-length candidates.
2. **No Database Extensions:** Fuzzy matching is computed in Python on candidates of the identical length. This eliminates dependencies on `pg_trgm` or privileged extension installations in restricted environments.
3. **Resilience & Snapshot Fallback:** An in-memory snapshot of active entries is cached and refreshed periodically. If PostgreSQL becomes unreachable, lookups transparently fall back to the snapshot, hits are buffered in memory and persisted on reconnection, and the pipeline reports `db_ok: false`. When `require_db: true`, production refuses to start if the database is down.
4. **Dedicated Async Worker Thread:** Watchlist lookups operate on a background thread fed by a bounded queue from ANPR events. Slow lookups never block YOLO detection, tracking, or OCR.
5. **Shared Normalization Rules:** Plate normalization reuses ANPR's `PlateFormats` and look-alike correction tables. Lookups and stored plates compare strictly normalized representations.
6. **Matching & Distance Metrics:**
   - `exact`: distance = 0.0, quality = 1.0.
   - `near`: same length, OCR-aware substitution distance $\le 1.0$. Look-alike swaps (e.g. `B/8`, `O/0`, `1/I`) cost 0.5; plain character substitutions cost 1.0. Quality $= 1 - 0.2 \times \text{distance}$. Different length strings are never near matches.
7. **Scoring & Alert Status Hierarchy:**
   - $\text{score} = \text{round}(100 \times \text{plate\_confidence} \times \text{quality})$.
   - Status is `alert` for exact matches where $\text{plate\_confidence} \ge \text{alert\_min\_confidence}$ (0.70).
   - Near matches and matches below the confidence threshold default to `review`.
   - Scores below `min_score` (40) are discarded.
8. **Deduplication & Cooldown:**
   - Per track: each distinct plate text is looked up once.
   - Per camera + watchlist entry: repeat alerts within `cooldown_s` (60s) are recorded as `suppressed` in `watchlist_hits` without emitting redundant events.
   - Status upgrade override: an alert inside the cooldown of a prior review status always emits an event.
9. **Full Hit History:** Every hit (including suppressed) is persisted to `watchlist_hits` with timestamps, camera ID, track ID, confidence, score, match type, and status.
10. **Soft Deletes and Audit Trail:** Entries are soft-deactivated (`active = false`), preserving foreign keys and history. All lifecycle operations (`ADD`, `UPDATE`, `DEACTIVATE`, `RESTORE`, `IMPORT`) append an immutable row to `watchlist_audit`.
11. **Minimal Event Payloads for Privacy:** `WATCHLIST_MATCH` events contain IDs, entity type, risk level, plate, score, and status, but omit human-identifiable names and descriptions. Roles and investigator permissions (Week 3) govern entry resolution.

## Schema Alignment
Columns adopt the Day 14 schema names (`watchlist_id`, `entity_type`, `identifier`, `normalized_identifier`, `name`, `description`, `risk_level`, `embedding`, `active`, `created_by`, `created_at`, `updated_at`).
