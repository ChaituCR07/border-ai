# Investigation Data Audit & Schema Inventory

## 1. Plate Storage and Normalisation
- **Primary Column:** `events.plate_number` (stored directly on `events` by Python pipeline sinks).
- **Secondary / Fallback:** `events.metadata->>'plate'` and `vehicles.plate_number` (linked via `vehicles.event_id = events.event_id`).
- **Unified Retrieval:** In SQL queries, plate is extracted using:
  `COALESCE(e.plate_number, e.metadata->>'plate', v.plate_number)`
- **Generated Columns (Migration 005):**
  - `plate_norm`: Uppercased alphanumeric string stripped of spaces and punctuation (`regexp_replace(upper(coalesce(plate_number, metadata->>'plate', '')), '[^A-Z0-9]', '', 'g')`).
  - `plate_key`: OCR confusable character mapping (`translate(plate_norm, 'OQDIBSZG', '00018526')`).

## 2. Event-to-Vehicle Entity Linking
- `vehicles` table holds physical sightings with consensus confidence (`confidence REAL`), `vehicle_class`, `plate_format`, and `final`.
- `vehicles.event_id` is a `UNIQUE` foreign key referencing `events.event_id` with `ON DELETE CASCADE`.
- Sighting queries join `events` to `vehicles` on `events.event_id = vehicles.event_id` or query by `vehicle_id`.

## 3. Person & Biometric Identifiers
- Stored exclusively as string identifiers within `events.metadata->>'person_id'` or `events.metadata->>'reid_candidate_id'`.
- Watchlist face-match hits store `metadata->>'subject_id'`.
- In compliance with ADR 0009 and ADR 0024:
  - No raw embeddings, face photos, or biometric templates are stored in search indexes or returned in search result DTOs.
  - Person candidate lookups are strictly identifier-based, restricted to `INVESTIGATOR` and `ADMIN` roles, and require an audited `purpose` string ($\ge 5$ characters).
  - Temporary Re-ID candidates expire automatically via the retention policy. Expired candidates simply return empty search results.

## 4. OCR Confusable Character Mapping
From `ai-engine/app/anpr/plate_format.py` and `ai-engine/app/watchlist/matcher.py`:
- `DIGIT_TO_LETTER = {"0": "O", "1": "I", "2": "Z", "4": "A", "5": "S", "6": "G", "7": "T", "8": "B"}`
- `LETTER_TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2", "A": "4", "S": "5", "G": "6", "T": "7", "B": "8"}`
- For canonical `plate_key` indexing and look-alike search:
  - Characters `O`, `Q`, `D` map to `0`
  - Character `I` maps to `1`
  - Character `B` maps to `8`
  - Character `S` maps to `5`
  - Character `Z` maps to `2`
  - Character `G` maps to `6`
  - SQL: `translate(plate_norm(t), 'OQDIBSZG', '00018526')`
  - TypeScript: `plateKey(s: string)` uses identical mapping map.

## 5. Event Types Inventory
Documented in `docs/api/event_types.md`:
- `RESTRICTED_ZONE_ENTRY`
- `ZONE_INTRUSION`
- `TRIPWIRE_CROSSING`
- `DIRECTION_VIOLATION`
- `LOITERING_DETECTED`
- `SPEED_ANOMALY`
- `ANPR_DETECTION`
- `WATCHLIST_HIT`
- `PERSON_DETECTED`
- `VEHICLE_DETECTED`
- `THREAT_ALERT`

## 6. Timestamp Precision & Timezone Filtering
- `events.timestamp` is `TIMESTAMPTZ` with microsecond resolution.
- Absolute range filtering uses `from` and `to` ISO strings in UTC.
- Time-of-day filtering uses `time_from` and `time_to` (`HH:MM`) evaluated in the requested IANA timezone `tz`:
  `((e."timestamp" AT TIME ZONE $tz)::time)`
  Supports overnight ranges (e.g. `22:00` to `05:00`) using `OR` logic.
