# Platform Configuration (`configs`)

The `configs/` directory stores declarative configuration files defining AI detection thresholds, camera streams, spatial security boundaries, behavioral rules, threat scoring weights, and watchlist seed datasets. Decoupling configuration from application code allows dynamic operational tuning without service rebuilds.

---

## 1. Directory Structure

```text
configs/
├── app.yaml                   # Global AI model, tracker, ANPR, and identity settings
├── cameras.json               # Camera inventory, stream sources, and target frame rates
├── rules.json                 # Behaviour rules (rules) and Threat Scoring engine (scoring)
├── authorized_plates_demo.csv # Authorized plate whitelist for rule R005
├── watchlist_demo.csv         # Initial watchlist entries for vehicles and persons
└── zones/
    └── CAM_001.json           # Per-camera normalized spatial polygons & virtual tripwires
```

---

## 2. Configuration Files & Schemas

### 2.1 `rules.json` — Behaviour Rules & Threat Scoring Configuration
This unified file configures both the **Behaviour Analysis Engine** (`rules`) and the **Threat Scoring Engine** (`scoring`):

```json
{
  "rules": [
    {
      "rule_id": "R001",
      "name": "Restricted Zone Entry",
      "event_type": "ZONE_VIOLATION",
      "severity": "HIGH",
      "points": 30,
      "enabled": true,
      "conditions": [
        {"type": "object", "value": ["person", "car", "truck", "bus", "motorcycle", "bicycle"]},
        {"type": "zone", "zone_type": "restricted"}
      ],
      "actions": [{"type": "alert", "severity": "HIGH", "score": 30}]
    }
  ],
  "scoring": {
    "max_score": 100,
    "window_s": 600,
    "alert_min_score": 10,
    "cooldown_s": 60,
    "rearm_s": 300,
    "merge_by_plate": true,
    "merge_scope": "camera",
    "levels": [
      {"name": "LOW", "min": 0},
      {"name": "MEDIUM", "min": 30},
      {"name": "HIGH", "min": 60},
      {"name": "CRITICAL", "min": 80}
    ],
    "bonus": {"multiple_suspicious": {"points": 10, "min_distinct_kinds": 4}},
    "sources": [
      {
        "id": "zone_violation",
        "label": "Restricted zone entry",
        "match": {"event_type": "ZONE_VIOLATION"},
        "points": "from_event"
      },
      {
        "id": "direction_violation",
        "label": "Unauthorized direction",
        "match": {"event_type": "DIRECTION_VIOLATION"},
        "points": "from_event"
      },
      {
        "id": "loitering",
        "label": "Loitering over 60 seconds",
        "match": {"event_type": "LOITERING_VIOLATION"},
        "points": "from_event"
      },
      {
        "id": "after_hours",
        "label": "After-hours movement",
        "match": {"event_type": "AFTER_HOURS_ACTIVITY"},
        "points": "from_event"
      },
      {
        "id": "unauthorized_vehicle_night",
        "label": "Unauthorized vehicle at night in a restricted zone",
        "match": {"event_type": "UNAUTHORIZED_VEHICLE_AFTER_HOURS"},
        "points": "from_event"
      },
      {
        "id": "line_crossing",
        "label": "Virtual line crossing",
        "match": {"event_type": "LINE_CROSSING", "where": {"rule_type": "tripwire"}},
        "points": 20,
        "excluded_by": ["direction_violation"]
      },
      {
        "id": "watchlist_vehicle",
        "label": "Watchlisted vehicle",
        "match": {"event_type": "WATCHLIST_MATCH", "where": {"details.entity_type": ["VEHICLE", "PLATE"]}},
        "points": 40,
        "status_multiplier": {"alert": 1.0, "review": 0.5}
      },
      {
        "id": "watchlist_person",
        "label": "Watchlisted person",
        "match": {"event_type": "WATCHLIST_MATCH", "where": {"details.entity_type": ["PERSON", "FACE"]}},
        "points": 50,
        "status_multiplier": {"alert": 1.0, "review": 0.5}
      }
    ]
  }
}
```

- **`max_score`:** Capping ceiling for total threat score (default 100).
- **`window_s`:** Active evidence lifetime in seconds (default 600s / 10 minutes).
- **`alert_min_score`:** Minimum aggregate score required to trigger any alert event (default 10).
- **`cooldown_s`:** Minimum interval between new alert episodes for an entity (default 60s).
- **`rearm_s`:** Quiet interval below threshold required before an entity can alert again (default 300s).
- **`merge_by_plate`:** Automatically merges track states for the same vehicle once an ANPR plate is recognized.
- **`excluded_by`:** Stops duplicate counting of the same incident (e.g. wrong-way line crossing).
- **`status_multiplier`:** Halves the weight of unconfirmed/review-status evidence (`0.5`).
- **`bonus`:** Awards +10 points when an entity triggers $\ge 4$ distinct kinds of suspicious evidence.

### 2.2 `app.yaml` — AI Model & Subsystem Configuration
Configures YOLOv8, ByteTrack, PaddleOCR, facial biometric settings, and the **Redis Event Pipeline**:

```yaml
events:
  enabled: false                          # Opt-in publishing; override via CLI (--publish)
  redis_url: redis://localhost:6379/0     # Connection URL (reads REDIS_URL or .env)
  stream: surveillance.events             # Primary event stream (MAXLEN ~100k)
  alerts_stream: surveillance.alerts      # High-priority threat alert copy (MAXLEN ~10k)
  dead_stream: surveillance.events.dead   # Poison / failed message quarantine (MAXLEN ~10k)
  alert_types: [THREAT_ALERT]             # Types copied to alerts_stream
  batch_size: 100                         # Events per network round-trip
  flush_ms: 50                            # Max publisher batch accumulation delay
  buffer_high: 5000                       # In-memory queue cap for alerts/violations
  buffer_low: 20000                       # In-memory queue cap for observation events
  retry_initial_s: 0.5                    # Initial reconnection backoff
  retry_max_s: 10.0                       # Maximum reconnection backoff
  shutdown_timeout_s: 10.0                # Graceful queue drain timeout at shutdown
  processor:
    group: processor                      # Consumer group name
    consumer: processor-1                 # Default worker identifier
    start: "0"                            # Group start position ("0" = all, "$" = new)
    block_ms: 1000                        # Max consumer block wait on empty stream
    batch: 50                             # Batch size per XREADGROUP
    reclaim_idle_ms: 30000                # Idle threshold before taking over stale PEL messages
    max_deliveries: 5                     # Max delivery attempts before dead-letter routing
    dedupe_cache: 20000                   # LRU cache size for processed event IDs
```

### 2.3 `cameras.json` — Camera Stream Inventory
Defines camera IDs, display names, physical locations, stream sources (video files or RTSP URLs), frame rate pacing, and resolution resizing. Seeded directly into the PostgreSQL `cameras` table via `scripts/seed_cameras.py`.

### 2.4 `zones/<CAMERA_ID>.json` — Spatial Polygons & Tripwires
Defines restricted areas and virtual boundary lines in normalized `[0.0, 1.0]` coordinates.

### 2.5 Demo Seed Datasets
- **`authorized_plates_demo.csv`:** Authorized vehicle whitelist for Section 38 rules (`KA01AB1234`, `DL08CZ9999`).
- **`watchlist_demo.csv`:** Initial operational watchlist entries with risk levels (`HIGH`, `CRITICAL`) and entity types (`VEHICLE`, `PERSON`).
