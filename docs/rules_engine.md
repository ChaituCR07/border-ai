# Behaviour Engine (Configurable Rules)

The **Behaviour Engine** is the deterministic decision layer in Border-AI. It transforms low-level computer vision **observations** into structured, severity-tagged, explainable **behaviour events**.

```
+--------------------------------------------------------------------------------+
|                             INFERENCE PIPELINE                                 |
|                                                                                |
|  [Track Engine]   [Zone Engine]   [Line Engine]   [ANPR Worker]  [Watchlist]  |
|         │                │               │               │             │       |
|      Tracks         ZONE_ENTER     LINE_CROSSING       PLATE       WATCHLIST   |
|         │           ZONE_EXIT      (direction)      RECOGNIZED       MATCH     |
|         ▼                ▼               ▼               ▼             ▼       |
|   ┌────────────────────────────────────────────────────────────────────────┐   |
|   │                       TrackContext (Per-Track)                         │   |
|   │  - object_class & track age                                            │   |
|   │  - active zones with dwell duration                                    │   |
|   │  - recent observation events (fifo 50)                                 │   |
|   │  - recognized plate & authorization status                             │   |
|   │  - highest severity watchlist hit                                      │   |
|   └──────────────────────────────────┬─────────────────────────────────────┘   |
|                                      │                                         |
|                                      ▼                                         |
|   ┌────────────────────────────────────────────────────────────────────────┐   |
|   │                BehaviourEngine (configs/rules.json)                    │   |
|   │  - pure condition evaluation (spatial, temporal, identity, logical)    │   |
|   │  - episode tracking & bindings (per zone / line)                       │   |
|   │  - re-arm duration & cooldown suppression                              │   |
|   └──────────────────────────────────┬─────────────────────────────────────┘   |
|                                      │                                         |
|                                      ▼                                         |
|                              BEHAVIOUR EVENTS                                  |
|                ZONE_VIOLATION, DIRECTION_VIOLATION, LOITERING,                 |
|                   AFTER_HOURS_ACTIVITY, UNAUTHORIZED_VEHICLE                   |
|                (severity, points, reasons, bindings, track_id)                 |
+────────────────────────────────────────────────────────────────────────────────+
```

---

## 1. Schema Reference (`configs/rules.json`)

Top-level configuration structure:
- `version`: Schema version (currently `1`).
- `site.timezone`: Default IANA timezone (e.g. `"Asia/Kolkata"`).
- `site.cameras`: Optional per-camera timezone dictionary (e.g. `{"CAM_002": {"timezone": "UTC"}}`).
- `authorized_plates_csv`: Relative path to authorized license plates CSV.
- `rules`: Array of rule definitions.

### Rule Attributes

| Field | Type | Required | Description | Default |
|---|---|---|---|---|
| `rule_id` | string | Yes | Unique rule identifier (e.g. `"R001"`) | - |
| `name` | string | Yes | Human-readable title | - |
| `description` | string | No | Operational explanation | `""` |
| `event_type` | string | Yes | Produced event type (`[A-Z0-9_]{3,41}`). Must not collide with observation names | - |
| `conditions` | array | Yes | Non-empty list of condition objects (implicit logical `AND`) | - |
| `action.severity` | string | Yes | `"LOW"`, `"MEDIUM"`, `"HIGH"`, or `"CRITICAL"` | - |
| `action.score` | integer | Yes | Threat points (0 to 100) | - |
| `enabled` | boolean | No | Master enable switch for rule | `true` |
| `cameras` | string[] | No | Scope rule to specific camera IDs | all cameras |
| `cooldown_s` | number | No | Minimum interval between alerts for same track | `0.0` |
| `rearm_s` | number | No | Time condition must stay false before re-firing | `30.0` |

### Condition Types

1. **`object`**: Matches track classification.
   `{"type": "object", "value": ["person", "car"]}`
2. **`zone`**: Evaluates zone presence and dwell time.
   `{"type": "zone", "zone_type": "restricted", "min_dwell_s": 0, "inside": true}`
3. **`line_crossing`**: Matches recent tripwire crossings with direction filtering.
   `{"type": "line_crossing", "line": "L1", "expected_direction": "IN", "within_s": 5}`
4. **`time`**: Local time window and weekday matching.
   `{"type": "time", "between": ["22:00", "05:00"], "days": ["MON", "TUE"]}`
5. **`plate`**: Validates OCR presence and authorization list membership.
   `{"type": "plate", "read": true, "authorized": false}`
6. **`watchlist`**: Matches watchlist hit presence, risk levels, and statuses.
   `{"type": "watchlist", "present": true, "status": ["alert"], "risk_level_min": "HIGH"}`
7. **`track_age`**: Minimum elapsed tracking duration in seconds.
   `{"type": "track_age", "min_s": 2.0}`
8. **`all` / `any`**: Logical AND / OR over nested conditions.
   `{"type": "any", "conditions": [...]}`
9. **`not`**: Logical negation of a nested condition.
   `{"type": "not", "condition": {...}}`

---

## 2. Core Rule Pack (Shipped Default)

The default rule pack in `configs/rules.json` contains five essential rules:

1. **`R001` - Restricted Zone Entry (`ZONE_VIOLATION`)**:
   Fires immediately when a person or vehicle enters a polygon marked `restricted`. (Severity: `HIGH`, Points: `30`).
2. **`R002` - Wrong Direction (`DIRECTION_VIOLATION`)**:
   Fires when an object crosses line `L1` in any direction other than `IN`. (Severity: `MEDIUM`, Points: `20`).
3. **`R003` - Loitering (`LOITERING_VIOLATION`)**:
   Fires when a person remains inside any zone for at least 60 seconds. (Severity: `MEDIUM`, Points: `15`).
4. **`R004` - After-Hours Activity (`AFTER_HOURS_ACTIVITY`)**:
   Fires when an object moves between 22:00 and 05:00 local time with track age >= 2s. (Severity: `LOW`, Points: `10`, rearm: 1 hour).
5. **`R005` - Unauthorized Vehicle in Restricted Zone After Hours (`UNAUTHORIZED_VEHICLE_AFTER_HOURS`)**:
   Section 38 composite rule combining vehicle type, restricted zone, night hours, and unauthorized plate. (Severity: `CRITICAL`, Points: `40`).

---

## 3. Operational Tools

### 1. Rule Validation (`scripts/rules_check.py`)
Validates `configs/rules.json` syntax, default values, and cross-references zones/lines against camera geometry files:
```bash
python scripts/rules_check.py --rules configs/rules.json
```

### 2. Fast Historical Replay (`scripts/replay_behaviour.py`)
Re-evaluates rule packs over recorded `events.jsonl` files in seconds without video or GPU inference:
```bash
python scripts/replay_behaviour.py --events outputs/runs/<run_id>/events.jsonl --rules configs/rules.json
```

### 3. Event Ground-Truth Verifier (`scripts/check_events.py`)
Automated verification of run summary event counts against ground truth:
```bash
python scripts/check_events.py --summary outputs/runs/<run_id>/summary.json \
    --expect docs/ground_truth/behaviour_person_walking.json --only ZONE_VIOLATION AFTER_HOURS_ACTIVITY
```

---

## 4. Known Limitations

- **Tracker ID Switching:** Dwell timers and track context belong to track IDs. If a tracker switches IDs due to heavy occlusion, dwell counters reset.
- **Unread Plate Handling:** An unread plate evaluates as neither authorized nor unauthorized; `plate.authorized: false` only triggers once a plate is confirmed not present in the authorized list.
- **Midnight Weekday Boundary:** For time windows spanning midnight (e.g. 22:00-05:00), the day of week is evaluated at the current instant in the configured timezone.
