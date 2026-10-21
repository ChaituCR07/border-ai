# AI Engine REST API Specification (`ai-engine`)

The AI Engine exposes a high-performance REST API on port `8000` for ad-hoc inference, model inspection, and health monitoring.

---

## 1. Endpoints Overview

| Method | Endpoint | Description | Content-Type |
|---|---|---|---|
| `GET` | `/health` | System health, environment, CUDA availability, and model status | `application/json` |
| `GET` | `/model/info` | Active YOLO model architecture, thresholds, classes, and stats | `application/json` |
| `POST` | `/detect` | Upload image, returns structured JSON detections | `multipart/form-data` → `application/json` |
| `POST` | `/detect/annotated` | Upload image, returns annotated JPEG with rendered bounding boxes | `multipart/form-data` → `image/jpeg` |

---

## 2. Request & Response Contracts

### `POST /detect`
Upload an image (`.jpg`, `.png`, etc.) via form-data.

#### Query Parameters:
- `camera_id` (string, optional, default: `"API"`): Camera tag associated with the frame.
- `conf` (float, optional, range: `0.0 - 1.0`): Confidence threshold override.
- `iou` (float, optional, range: `0.0 - 1.0`): NMS IoU threshold override.

#### Example Response:
```json
{
  "camera_id": "CAM_001",
  "frame_id": 0,
  "timestamp": "2026-10-04T16:15:32.481Z",
  "frame_size": {
    "width": 1280,
    "height": 720
  },
  "inference_ms": 14.2,
  "objects": [
    {
      "class": "person",
      "class_id": 0,
      "confidence": 0.912,
      "bbox": [412.3, 188.0, 497.9, 402.6]
    },
    {
      "class": "car",
      "class_id": 2,
      "confidence": 0.874,
      "bbox": [60.1, 300.4, 310.8, 470.2]
    }
  ]
}
```

> **Bounding Box Convention:** `bbox` is an array of 4 floats: `[x1, y1, x2, y2]` in absolute pixel coordinates corresponding to `frame_size`.

---

## 3. Error Responses

| HTTP Status | Meaning | Typical Cause |
|---|---|---|
| `400 Bad Request` | Could not decode image | Uploaded file is corrupt or not an image. |
| `413 Payload Too Large` | Image exceeds 10 MB limit | Uploaded raw file is larger than 10 MB. |
| `503 Service Unavailable` | Detector not loaded | Model is still initializing during cold startup. |

---

## 4. Tracking Output Contract (`FrameTracks`)

The tracking pipeline (`ai-engine/scripts/track_cameras.py` and downstream streaming modules) extends detection outputs with persistent tracking semantics.

### JSON Schema Structure:
```json
{
  "camera_id": "CAM_001",
  "frame_id": 42,
  "timestamp": "2026-10-05T16:22:30.125Z",
  "frame_size": {
    "width": 1280,
    "height": 720
  },
  "inference_ms": 45.2,
  "objects": [
    {
      "track_id": 14,
      "class": "person",
      "confidence": 0.892,
      "bbox": [412.3, 188.0, 497.9, 402.6],
      "age_s": 3.4
    }
  ]
}
```

### Tracking Fields:
- `track_id` (integer): Persistent object identifier unique within `camera_id`.
- `class` (string): Stable majority-voted class name across the track's lifetime (eliminates single-frame classification flicker).
- `age_s` (float): Track age in seconds since first activation.
- `bbox` (array of 4 floats): `[x1, y1, x2, y2]` clamped pixel coordinates.
- *Note:* `class_id` is intentionally omitted from the tracking contract because `class` reflects the confidence-weighted majority vote, which may supersede individual frame-level class indices.

---

## 5. Analytics Event Contract (`Event`)

Spatial events dispatched by `RuleEngine` to event log streams (`outputs/events/events_*.jsonl`) and Redis Streams (Week 2):

### JSON Schema Structure:
```json
{
  "event_id": "9b1deb4d3b7d4bad9bdd2b0d7b3dcb6d",
  "type": "ZONE_ENTER",
  "camera_id": "CAM_001",
  "timestamp": "2026-10-06T16:22:30.125Z",
  "frame_id": 142,
  "track_id": 14,
  "object": {
    "class": "person",
    "confidence": 0.892,
    "bbox": [412.3, 188.0, 497.9, 402.6]
  },
  "rule": {
    "id": "Z1",
    "name": "Restricted Zone",
    "kind": "zone",
    "type": "restricted"
  },
  "direction": null,
  "dwell_s": null,
  "details": {
    "spawned_inside": false,
    "anchor": [455.1, 402.6]
  }
}
```

### Event Fields:
- `event_id`: Universally unique 32-character hexadecimal identifier.
- `type`: One of `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL`, `LOITERING`, `LINE_CROSSING`.
- `direction`: `"IN"` or `"OUT"` for `LINE_CROSSING`; `null` for zone events.
- `dwell_s`: Total duration spent inside the zone in seconds for `ZONE_DWELL`, `LOITERING`, and `ZONE_EXIT`.
- `details.spawned_inside`: Indicates whether the track was already inside the zone upon initial confirmation.

## 3. ANPR Events & Plate Records (Day 8)

### Event Type: `PLATE_RECOGNIZED`
Emitted by the ANPR service when a tracked vehicle's license plate reaches consensus stability (`final: false`), and finalized upon tracker removal if updated or previously un-emitted (`final: true`).

```json
{
  "event_id": "7a35e4d812344efaa111b222c333d444",
  "type": "PLATE_RECOGNIZED",
  "camera_id": "CAM_002",
  "timestamp": "2026-10-12T14:30:15.250Z",
  "frame_id": 142,
  "object": {
    "track_id": 42,
    "class": "car",
    "confidence": 0.884,
    "bbox": [520.0, 310.0, 780.0, 520.0]
  },
  "rule": {
    "id": "ANPR",
    "name": "Plate recognition",
    "kind": "anpr",
    "type": "plate"
  },
  "details": {
    "plate": "KA01AB1234",
    "reads": 5,
    "votes": 4,
    "agreement": 0.800,
    "format": "strict",
    "method": "exact",
    "final": false,
    "video_time_s": 9.47
  }
}
```

### Plate Record Schema (`anpr/plates.jsonl`)
Stored once a vehicle plate achieves stability and upon vehicle departure:

```json
{
  "vehicle_id": 42,
  "plate": "KA01AB1234",
  "confidence": 0.884,
  "camera_id": "CAM_002",
  "vehicle_class": "car",
  "reads": 5,
  "votes": 4,
  "agreement": 0.800,
  "format": "strict",
  "final": true,
  "method": "exact",
  "first_seen": "2026-10-12T14:30:05.120Z",
  "last_seen": "2026-10-12T14:30:18.540Z",
  "read_log": [
    ["KA01AB1234", 0.94],
    ["KA01AB1234", 0.92],
    ["KA01AB1284", 0.81],
    ["KA01AB1234", 0.95],
    ["KA01AB1234", 0.93]
  ]
}
```

---

## Watchlist Match Event (`WATCHLIST_MATCH`)

Emitted when a recognized vehicle license plate matches an active entity on the watchlist.

### Event Format (`events.jsonl`)
```json
{
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "camera_id": "CAM_002",
  "timestamp": "2026-10-14T15:30:10.500Z",
  "frame_id": 450,
  "type": "WATCHLIST_MATCH",
  "track_id": 42,
  "plate": "KA01AB1234",
  "score": 91,
  "object_class": "car",
  "confidence": 0.91,
  "bbox": [120.0, 340.0, 480.0, 610.0],
  "rule_id": "WATCHLIST",
  "rule_name": "Watchlist match",
  "rule_kind": "watchlist",
  "rule_type": "vehicle",
  "details": {
    "plate": "KA01AB1234",
    "score": 91,
    "status": "alert",
    "review_required": false,
    "entry_id": 1,
    "entity_type": "VEHICLE",
    "risk_level": "HIGH",
    "match_type": "exact",
    "distance": 0.0,
    "matched_identifier": "KA01AB1234",
    "plate_confidence": 0.912,
    "also_matched": [],
    "plate_event_id": "3d5f..."
  }
}
```

### Privacy & RBAC Protection
To prevent information leakage across public logs and message queues, the entry's `name` and `description` are **deliberately excluded** from the event payload. The web dashboard resolves human metadata by querying `entry_id` against the PostgreSQL database under authenticated Investigator and Admin roles.

---

## Face Watchlist Match Event (`WATCHLIST_MATCH`)

Emitted when an enrolled face embedding matches a tracked person.

```json
{
  "event_id": "8c3b7a1d-2e4f-4a9b-bc11-9a8f2e3d4c5b",
  "camera_id": "CAM_001",
  "timestamp": "2026-10-18T16:20:05.100Z",
  "frame_id": 412,
  "type": "WATCHLIST_MATCH",
  "track_id": 14,
  "confidence": 0.85,
  "object_class": "person",
  "bbox": [100.0, 20.0, 200.0, 200.0],
  "rule_id": "FACE_WATCHLIST",
  "rule_name": "Face watchlist match",
  "rule_kind": "watchlist",
  "rule_type": "face",
  "details": {
    "match_basis": "face",
    "score": 85,
    "status": "review",
    "review_required": true,
    "similarity": 0.725,
    "margin": 0.182,
    "embeddings": 4,
    "consistency": 0.892,
    "entry_id": 1,
    "entity_type": "FACE",
    "risk_level": "HIGH",
    "embedding_model": "sface-opencv"
  }
}
```

---

## Cross-Camera Re-ID Candidate Event (`REID_MATCH`)

Emitted when a person track exhibits high visual appearance similarity to a recently seen track on another camera.

```json
{
  "event_id": "5f1a2b3c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "camera_id": "CAM_002",
  "timestamp": "2026-10-18T16:25:30.400Z",
  "frame_id": 780,
  "type": "REID_MATCH",
  "track_id": 28,
  "confidence": 0.941,
  "object_class": "person",
  "bbox": [140.0, 50.0, 260.0, 290.0],
  "rule_id": "REID",
  "rule_name": "Cross-camera appearance match",
  "rule_kind": "identity",
  "rule_type": "reid",
  "details": {
    "status": "candidate",
    "review_required": true,
    "similarity": 0.941,
    "samples": 5,
    "embedder": "color-layout",
    "candidates": [
      {
        "camera_id": "CAM_001",
        "track_id": 14,
        "similarity": 0.941,
        "gap_s": 42.5
      }
    ]
  }
}
```


### Behaviour Event (`ZONE_VIOLATION`, `DIRECTION_VIOLATION`, `LOITERING_VIOLATION`, `AFTER_HOURS_ACTIVITY`, `UNAUTHORIZED_VEHICLE_AFTER_HOURS`)

Emitted when deterministic behaviour rules evaluate to true for an active track.

```json
{
  "event_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "camera_id": "CAM_001",
  "timestamp": "2026-10-12T02:13:00.000Z",
  "frame_id": 142,
  "type": "ZONE_VIOLATION",
  "event": "ZONE_VIOLATION",
  "severity": "HIGH",
  "track_id": 17,
  "confidence": 1.0,
  "object_class": "person",
  "bbox": [180.0, 110.0, 240.0, 290.0],
  "rule": {
    "id": "R001",
    "name": "Restricted Zone Entry",
    "kind": "behaviour",
    "type": "rule"
  },
  "direction": null,
  "dwell_s": null,
  "details": {
    "severity": "HIGH",
    "points": 30,
    "rule_id": "R001",
    "description": "A person or vehicle is inside a restricted zone",
    "reasons": [
      "object is a person",
      "inside zone Z1 (restricted) for 1 s"
    ],
    "bindings": {
      "zone_id": "Z1"
    },
    "track_age_s": 9.2
  }
}
```

### Threat Alert Event (`THREAT_ALERT`)

Emitted when an entity's aggregate threat score crosses the minimum alert threshold or escalates to a higher threat level.

```json
{
  "event_id": "9f8e7d6c-5b4a-3210-fedc-ba9876543210",
  "camera_id": "CAM_001",
  "timestamp": "2026-10-12T02:13:05.000Z",
  "frame_id": 150,
  "type": "THREAT_ALERT",
  "severity": "HIGH",
  "threat_score": 60,
  "track_id": 3,
  "confidence": 0.6,
  "object_class": "person",
  "bbox": [180.0, 110.0, 240.0, 290.0],
  "rule": {
    "id": "THREAT",
    "name": "Threat score",
    "kind": "threat",
    "type": "high"
  },
  "direction": null,
  "dwell_s": null,
  "details": {
    "alert_id": "e2b3c4d5f6a74b8c9d0e1f2a3b4c5d6e",
    "threat_score": 60,
    "severity": "HIGH",
    "priority": "HIGH",
    "level": "HIGH",
    "previous_level": "MEDIUM",
    "escalation": true,
    "summary": "HIGH (60/100): Restricted zone entry +30, Virtual line crossing +20, After-hours movement +10",
    "capped": false,
    "window_s": 600.0,
    "entity": "CAM_001#3",
    "plate": null,
    "snapshot_path": "snapshots/e2b3c4d5f6a74b8c9d0e1f2a3b4c5d6e.jpg",
    "contributions": [
      {
        "kind": "zone_violation",
        "label": "Restricted zone entry",
        "points": 30,
        "event_type": "ZONE_VIOLATION",
        "event_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
        "at": "2026-10-12T02:13:05.000Z",
        "reasons": ["inside zone Z1 (restricted) for 1 s"]
      },
      {
        "kind": "line_crossing",
        "label": "Virtual line crossing",
        "points": 20,
        "event_type": "LINE_CROSSING",
        "event_id": "6a5b4c3d-2e1f-0a9b-8c7d-6e5f4a3b2c1d",
        "at": "2026-10-12T02:13:02.000Z",
        "reasons": ["Virtual line crossing"]
      },
      {
        "kind": "after_hours",
        "label": "After-hours movement",
        "points": 10,
        "event_type": "AFTER_HOURS_ACTIVITY",
        "event_id": "5a4b3c2d-1e0f-9a8b-7c6d-5e4f3a2b1c0d",
        "at": "2026-10-12T02:13:00.000Z",
        "reasons": ["time 02:13 is between 22:00 and 05:00"]
      }
    ],
    "excluded": []
  }
}
```

#### Mapping to Day 14 Database Schema
- `events.severity` $\leftarrow$ `severity` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `events.threat_score` $\leftarrow$ `threat_score` (integer $0..100$)
- `alerts.priority` $\leftarrow$ `details.priority` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `alerts.snapshot_path` $\leftarrow$ `details.snapshot_path`
