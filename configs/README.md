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
Configures YOLOv8, ByteTrack, PaddleOCR, and facial biometric settings.

### 2.3 `cameras.json` — Camera Stream Inventory
Defines camera IDs, stream sources (video files or RTSP URLs), frame rate pacing, and resolution resizing.

### 2.4 `zones/<CAMERA_ID>.json` — Spatial Polygons & Tripwires
Defines restricted areas and virtual boundary lines in normalized `[0.0, 1.0]` coordinates.

### 2.5 Demo Seed Datasets
- **`authorized_plates_demo.csv`:** Authorized vehicle whitelist for Section 38 rules (`KA01AB1234`, `DL08CZ9999`).
- **`watchlist_demo.csv`:** Initial operational watchlist entries with risk levels (`HIGH`, `CRITICAL`) and entity types (`VEHICLE`, `PERSON`).
