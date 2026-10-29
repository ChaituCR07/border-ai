# ADR 0023 — Forensic Plate Normalization, Look-Alike Matching, and Time-of-Day Search Semantics

## Status
Accepted

## Context
Investigating cross-border incidents requires locating vehicles and suspects across cameras using partial, mistyped, or OCR-degraded license plates and time-of-day filters (e.g. "vehicles passing between 22:00 and 04:00 at night"). 

Differences between OCR recognition engines (Python), API query builders (Node.js/TypeScript), and database query planners (PostgreSQL) easily introduce subtle discrepancies where searches succeed in one layer but fail in another. Furthermore, time-of-day filters that cross midnight or daylight saving time transitions risk either omitting critical records or executing table scans over millions of rows.

## Decisions

1. **Tri-Lingual Parity for Plate Normalization and Confusable Characters:**
   - License plate text is cleaned by uppercasing and stripping non-alphanumeric characters.
   - For standard Indian plates, regex window parsing fits standard layout patterns (`LL[D]DDLL[L]DDDD`).
   - Confusable OCR characters are normalized using a shared character replacement table:
     - Digits to look-alike letters / letters to look-alike digits:
       - `O, Q, D` $\to$ `0`
       - `I, L` $\to$ `1`
       - `Z` $\to$ `2`
       - `A` $\to$ `4`
       - `S` $\to$ `5`
       - `G` $\to$ `6`
       - `T` $\to$ `7`
       - `B` $\to$ `8`
   - Exact parity is verified across Python (`ai-engine/anpr/plate.py`), TypeScript (`backend/src/common/plate.ts`), and PostgreSQL (`database/migrations/005_investigation_support.sql`) using a shared test fixture `docs/fixtures/plate_matching_cases.json`.

2. **Generated Columns and Specialized PostgreSQL Search Indexes:**
   - Migration `005_investigation_support.sql` adds generated columns:
     - `plate_norm`: cleaned, canonical alphanumeric plate string.
     - `plate_key`: confusable-reduced key where all look-alike characters are mapped to canonical numbers.
   - Database indexes:
     - B-Tree indexes on `plate_norm` and `plate_key` for exact, look-alike, and prefix matching.
     - Trigram index using `pg_trgm` (`gin (plate_norm gin_trgm_ops)`) for partial/substring contains matching.

3. **Safe LIKE Escaping:**
   - User inputs for `prefix` and `contains` plate searches are sanitized through `escapeLike()` which escapes `\`, `%`, and `_` with backslashes and forces `ESCAPE '\'` in SQL to prevent wildcard denial-of-service or unintended match broadening.

4. **Time-of-Day Window Semantics:**
   - Time-of-day searches (`time_from` and `time_to` in `HH:MM`) require explicit date bounds (`from` and `to`) spanning $\le 90$ days.
   - Timezone conversion is computed in PostgreSQL via `((e."timestamp" AT TIME ZONE $tz)::time)`.
   - Overnight wraps (`time_from > time_to`, e.g. `22:00 -> 05:00`) are evaluated using disjunctive range logic: `(t >= from OR t < to)`.

5. **Keyset Cursor Pagination Sort Stability:**
   - The API supports dual sorting: `sort=time` (default) and `sort=score` (threat priority).
   - In `sort=score` mode, cursor tuples encode `(threat_score, timestamp, event_id)` to guarantee stable traversal even when many events share identical threat scores.
   - Cursors encode their sort mode; submitting a `sort=time` cursor to a `sort=score` query is rejected with HTTP 400 `VALIDATION_ERROR`.

## Consequences
- 100% deterministic query results regardless of whether evaluation occurs in Python, TypeScript, or PostgreSQL.
- Fast index-assisted forensic queries across multi-million row event archives.
- Clear error feedback on invalid or ambiguous time-of-day boundaries.
