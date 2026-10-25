# Database Contract & Schema Audit (Python AI Engine <-> Node.js API)

**Reference Date:** 2026-10-25  
**Schema Level:** 003_core_schema + 004_api_support  
**Status:** Approved  

---

## 1. Table Definitions & Column Mappings

### `events` (Written by Python `PostgresEventSink`, Read-Only for Node.js API)
- `event_id` (TEXT, PK): UUIDv4 generated at source by computer vision pipeline. Stable public identifier.
- `event_seq` (BIGINT, IDENTITY, UNIQUE): Sequential integer. Formatted as `EVT_000129` via `event_ref(event_seq)`.
- `camera_id` (TEXT, FK -> `cameras.camera_id`): Identifier of the camera node.
- `event_type` (TEXT): Category string (e.g., `ZONE_VIOLATION`, `LINE_CROSSING`, `THREAT_ALERT`, `PLATE_RECOGNIZED`, `TRACK_SUMMARY`).
- `track_id` (BIGINT): Object tracking ID.
- `severity` (TEXT, Nullable): Enum (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- `threat_score` (INTEGER, Nullable): Integer in range 0–100 (populated for `THREAT_ALERT`).
- `timestamp` (TIMESTAMPTZ): Physical occurrence time (microsecond precision).
- `snapshot_path` (TEXT, Nullable): Path relative to `outputs/runs/` (e.g. `RUN_XXX/snapshots/file.jpg`).
- `plate_number` (TEXT, Nullable): Recognized license plate string.
- `object_class` (TEXT, Nullable): YOLO detection class (`person`, `car`, etc.).
- `rule_id` (TEXT, Nullable): Rule ID triggered (`R001` - `R005`).
- `rule_kind` (TEXT, Nullable): Classification of rule (`zone`, `line`, `behaviour`, `threat`).
- `run_id` (TEXT): Execution run folder identifier.
- `metadata` (JSONB): Full lossless event payload.
- `received_at` (TIMESTAMPTZ): Database write arrival time.

### `alerts` (Created by Python, Lifecycle Managed by Node.js API)
- `alert_id` (TEXT, PK): Unique alert identifier (e.g., `ALR_00001`).
- `event_id` (TEXT, FK -> `events.event_id`, ON DELETE CASCADE): Originating `THREAT_ALERT` event.
- `camera_id` (TEXT, FK -> `cameras.camera_id`): Originating camera.
- `priority` (TEXT): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `threat_score` (INTEGER): Integer 0–100.
- `status` (TEXT): State machine: `NEW` (or `OPEN`), `ACKNOWLEDGED`, `IN_PROGRESS`, `RESOLVED`, `FALSE_POSITIVE`.
- `entity` (TEXT): Grouping key (e.g., `plate:KA01AB1234` or `CAM_1#7`).
- `summary` (TEXT): Human-readable explanation summary.
- `acknowledged_by` (TEXT, Nullable): Operator username. Mandatory when status != `NEW`.
- `acknowledged_at` (TIMESTAMPTZ, Nullable): Timestamp of acknowledgement.
- `resolved_at` (TIMESTAMPTZ, Nullable): Timestamp of resolution.
- `created_at` (TIMESTAMPTZ): Physical event occurrence time.
- `updated_at` (TIMESTAMPTZ): Last workflow state modification.

### `alert_history` (Appended by Python on Creation, Appended by Node.js on Transition)
- `history_id` (BIGSERIAL, PK)
- `alert_id` (TEXT, FK -> `alerts.alert_id`)
- `from_status` (TEXT, Nullable): Previous status (`NULL` on initial creation).
- `to_status` (TEXT): New status.
- `actor` (TEXT): Operator identifier or `system`.
- `note` (TEXT): Operational justification note.
- `at` (TIMESTAMPTZ): Transition timestamp.

### `cameras` (Seeded by Script / Python Auto-Registration, Full CRUD via Node.js API)
- `camera_id` (TEXT, PK): Unique camera identifier (`^[A-Za-z0-9_.-]{1,64}$`).
- `name` (TEXT): Friendly label.
- `location` (TEXT): Physical zone or sector.
- `location_label` (TEXT): Optional extended location description.
- `rtsp_url` (TEXT, Nullable): Masked stream URL without credentials.
- `credentials_ref` (TEXT, Nullable): Named reference to environment secret.
- `status` (TEXT): `ACTIVE`, `INACTIVE`, `OFFLINE`, `MAINTENANCE`, `UNREGISTERED`.
- `enabled` (BOOLEAN): Active switch for pipeline processing.
- `metadata` (JSONB): Dynamic configuration attributes (`source_type`, `target_fps`).
- `created_at` / `updated_at` (TIMESTAMPTZ).

### `watchlist` (Read by Python Engine, Managed by Node.js API)
- `watchlist_id` (BIGSERIAL, PK)
- `entity_type` (TEXT): `VEHICLE`, `PLATE`, `PERSON`, `FACE`.
- `identifier` (TEXT): Raw input string.
- `normalized_identifier` (TEXT): Stripped/canonical string for matching.
- `name` (TEXT): Entity label.
- `description` / `notes` (TEXT).
- `risk_level` (TEXT): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `embedding` (BYTEA, Nullable): Private biometric embedding (excluded from API responses).
- `consent_reference` (TEXT, Nullable): Mandatory consent ID for `PERSON` entities.
- `active` (BOOLEAN): Soft-delete flag (`active=true` for active records).
- `deleted_at` (TIMESTAMPTZ, Nullable).
- `created_by` / `created_at` / `updated_at`.

### `api_audit_log` (Written by Node.js API for Administrative Actions)
- `audit_id` (BIGSERIAL, PK)
- `at` (TIMESTAMPTZ, DEFAULT `now()`)
- `actor` (TEXT)
- `action` (TEXT): `CAMERA_CREATE`, `CAMERA_UPDATE`, `WATCHLIST_CREATE`, `WATCHLIST_DELETE`, `ALERT_ACK`.
- `entity_type` (TEXT)
- `entity_id` (TEXT)
- `request_id` (TEXT)
- `detail` (JSONB)

---

## 2. Key Architectural Guarantees & Constraints

1. **Microsecond Timestamp Precision:**
   - PostgreSQL `TIMESTAMPTZ` stores microsecond timestamps.
   - Node.js `pg` driver is configured with custom type parsers (`pg.types.setTypeParser(1184, v => v)`) returning raw strings to prevent JavaScript `Date` 1-millisecond truncation.
   - Keyset pagination strictly compares `(timestamp, event_id) < ($1::timestamptz, $2::text)` to guarantee stable pagination under high ingestion rates.

2. **Zero-Credential API Principle:**
   - Camera stream endpoints reject `rtsp://user:pass@host` with `422 CREDENTIALS_IN_URL`.
   - Credentials are named references (`credentials_ref`) resolved in secure worker environments.

3. **Biometric Privacy Safeguards:**
   - The REST API is strictly non-biometric.
   - Facial image uploads and embedding vectors are rejected on `POST /api/watchlist` (`400 VALIDATION_ERROR`).
   - `embedding` is permanently omitted from API serialization.
   - `PERSON` watchlist entries mandate `consent_reference` (`422 CONSENT_REQUIRED`).

4. **Snapshot Sandboxing:**
   - Evidence frames are stored under a sandboxed directory (`outputs/runs/`).
   - `GET /api/snapshots/*` resolves absolute paths and enforces `abs.startsWith(root + path.sep)`, defeating path traversal attempts.
