# Border-AI Backend REST API Documentation

**Service:** Backend REST API (Node.js 22/24 LTS + TypeScript + Fastify + Zod + pg)  
**Port:** `4000` (default)  
**OpenAPI Spec:** Available dynamically at `/openapi.json` and interactive UI at `/docs` (exported statically at [openapi.json](file:///Users/chaitanyamedam/Downloads/border-ai/docs/api/openapi.json)).

---

## 1. Overview & Data Ownership

The Border-AI Backend REST API provides typed, validated, and high-performance access to the platform's video analytics, alerts, cameras, watchlist, and operational intelligence stored in PostgreSQL.

### Strict Data Ownership Model (ADR 0014)

| Table | Python AI Engine | Node.js REST API |
|---|---|---|
| `events`, `detections`, `vehicles` | **Exclusive Writer** | Read-Only |
| `alerts` | **Creates initial records** (`NEW`) | Reads + **Status transitions only** (`PATCH /acknowledge`) |
| `cameras` | Auto-registers on first event | Full administrative CRUD |
| `watchlist` | Reads (real-time plate & face match) | Full CRUD (strictly non-biometric fields) |
| `api_audit_log` | — | **Exclusive Writer** |

---

## 2. Endpoints Reference

### 2.1 Cameras (`/api/cameras`)

| Method | Endpoint | Description | Auth Role |
|---|---|---|---|
| `GET` | `/api/cameras` | List registered cameras with optional filters (`enabled`, `q`) | Viewer+ |
| `POST` | `/api/cameras` | Register a new camera with credential guard (`Location` header returned) | Admin |
| `GET` | `/api/cameras/:id` | Get single camera detail and live view URL | Viewer+ |
| `PUT` | `/api/cameras/:id` | Update mutable camera properties (location, RTSP URL, enabled) | Admin |

**Security Rules:**
- `stream_url` must use `rtsp`, `rtsps`, `http`, `https`, or `file`.
- URLs containing plaintext credentials (`://user:pass@`) are **strictly rejected** with `400 VALIDATION_ERROR` (`CREDENTIALS_IN_URL`). Credentials must be referenced indirectly by name via `credentials_ref`.
- `live_view_url` is dynamically computed from `MJPEG_BASE_URL` (`http://localhost:8001/cam/{id}.mjpg`).

---

### 2.2 Events (`/api/events`)

| Method | Endpoint | Description | Auth Role |
|---|---|---|---|
| `GET` | `/api/events` | Keyset-paginated list of surveillance events with multi-param filters | Operator+ |
| `GET` | `/api/events/:id` | Full event detail including alert state, explanation, and snapshot availability | Operator+ |

**Query Parameters:**
- `camera_id` (string): Filter by camera identifier.
- `event_type` (string): Comma-separated event types (e.g., `RESTRICTED_ZONE_ENTRY,LINE_CROSSING`).
- `severity` (string): Comma-separated severities (`LOW,MEDIUM,HIGH,CRITICAL`).
- `min_score` / `max_score` (number 0..100): Threat score range.
- `from` / `to` (ISO-8601 UTC with tz): Query time span (maximum 90 days).
- `plate` (string): Exact plate search (normalised automatically).
- `limit` (int 1..200, default 50): Page size.
- `cursor` (base64url): Opaque keyset cursor encoding `(timestamp, event_id)`.

**Detail Output:**
Returns threat score explanation (`explanation.factors`) pass-through directly from the Python threat scorer (ADR 0012). Does not recompute scores in Node.

---

### 2.3 Alerts (`/api/alerts`)

| Method | Endpoint | Description | Auth Role |
|---|---|---|---|
| `GET` | `/api/alerts` | List alerts filtered by `status`, `priority`, `camera_id`, `from`, `to` | Operator+ |
| `PATCH` | `/api/alerts/:id/acknowledge` | Acknowledge alert (atomic, idempotent, and concurrency-safe) | Operator+ |

**Acknowledge Semantics (ADR 0016):**
- Uses atomic SQL:
  ```sql
  UPDATE alerts
     SET status = 'ACKNOWLEDGED', acknowledged_by = $2, acknowledged_at = now()
   WHERE alert_id = $1 AND status IN ('NEW', 'OPEN')
  RETURNING *;
  ```
- Repeated calls return `200 OK` with the existing state without overwriting the original acknowledger or timestamp, and without emitting duplicate audit records.

---

### 2.4 Watchlist (`/api/watchlist`)

| Method | Endpoint | Description | Auth Role |
|---|---|---|---|
| `GET` | `/api/watchlist` | List active watchlist items (`include_deleted=true` for audit) | Investigator+ |
| `POST` | `/api/watchlist` | Create watchlist entry (strictly non-biometric) | Investigator+ |
| `DELETE` | `/api/watchlist/:id` | Soft-delete entry (`active = false`, `deleted_at = now()`) | Investigator+ |

**Privacy & Validation Rules:**
- `VEHICLE`: License plates are normalised identically to the Python ANPR module (removes punctuation/spaces, uppercase, OCR lookalike corrections).
- `PERSON`: Requires non-empty `consent_reference` (ADR 0009). Missing reference triggers `400 VALIDATION_ERROR` (`CONSENT_REQUIRED`).
- **Strictly Non-Biometric:** Request bodies containing `embedding`, `image`, `face`, or `photo` are rejected. Biometrics are enrolled exclusively via Python offline tools.

---

### 2.5 Analytics (`/api/analytics`)

| Method | Endpoint | Description | Auth Role |
|---|---|---|---|
| `GET` | `/api/analytics/events` | Zero-filled time-series buckets (`hour` or `day`) in UTC | Viewer+ |
| `GET` | `/api/analytics/cameras` | Per-camera activity, open alerts, and max threat score | Viewer+ |
| `GET` | `/api/analytics/threats` | Severity distribution, score histograms, top event types & plates | Viewer+ |

---

### 2.6 Evidence Snapshots & Probes

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/snapshots/*` | Safe static evidence file serving with path traversal protection |
| `GET` | `/api/health` | Service liveness probe (200 OK) |
| `GET` | `/api/ready` | Database connection readiness probe (200 OK / 503 Service Unavailable) |

---

## 3. Keyset Cursor Pagination & Timestamps (ADR 0015)

The API avoids `OFFSET` pagination to ensure zero page drift on live surveillance feeds.

### Response Envelope
```json
{
  "data": [ ... ],
  "meta": {
    "limit": 50,
    "next_cursor": "eyJ0IjoiMjAyNi0xMC0yNVQwMjoyNTowMC4xMjM0NTZaIiwiaWQiOiIwYjBlOWYxYS0zYTIxLT..."
    "has_more": true
  }
}
```

The cursor is an opaque base64url JSON object `{ t: string, id: string }` where `t` preserves microsecond timestamps.

---

## 4. Standard Error Envelope

Every non-2xx response follows a uniform JSON structure with request correlation:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "path": "limit", "issue": "Number must be less than or equal to 200" }
    ],
    "request_id": "7c1a0c1e-3f82-4919-9d62-c07a3c7ef2b1"
  }
}
```

Standard codes: `VALIDATION_ERROR` (400), `UNAUTHENTICATED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409), `RATE_LIMITED` (429), `INTERNAL` (500).
