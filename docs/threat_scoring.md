# Threat Scoring Engine Guide

The **Threat Scoring Engine** combines real-time geometric observations, identity matches, and behavioural events into an explainable 0–100 threat score and 4-tier alert level.

```text
+---------------------------------------------------------------------------------+
|                       EVIDENCE INGESTION & PIPELINE                             |
|                                                                                 |
|  Geometric Observations       Watchlist Hits          Behaviour Events          |
|  (LINE_CROSSING, ZONE_ENTER)  (WATCHLIST_MATCH)       (ZONE_VIOLATION, etc.)    |
|                |                      |                         |               |
|                +----------------------+-------------------------+               |
|                                       v                                         |
|                         ThreatScorer.observe(cam, events)                       |
|                                       v                                         |
|                 Entity State Resolution (Plate Merging & Tracker)               |
|                                       v                                         |
|                     Sliding Window Expiry (window_s: 600s)                      |
|                                       v                                         |
|                    Occurrence Limiting (max_occurrences: 1)                     |
|                                       v                                         |
|                   Deduplication & Exclusion (excluded_by)                       |
|                                       v                                         |
|                  Multi-Suspicious Bonus (4 distinct kinds: +10)                 |
|                                       v                                         |
|                     Score Capping (min(raw_score, 100))                         |
|                                       v                                         |
|               Level Mapping (LOW, MEDIUM, HIGH, CRITICAL)                       |
|                                       v                                         |
|                    Escalation Filter & Re-Arm State Machine                     |
|                                       v                                         |
|                            THREAT_ALERT Raised                                  |
|                 (Includes Summary, Points, Snapshot & Evidence)                 |
+---------------------------------------------------------------------------------+
```

---

## 1. Threat Scoring Table

| Evidence Kind | Origin / Event Type | Planned Points | Conditions / Rules |
|---|---|---|---|
| `zone_violation` | `ZONE_VIOLATION` | from event (30) | Entry into restricted zone |
| `direction_violation` | `DIRECTION_VIOLATION` | from event (20) | Movement opposing authorized flow |
| `loitering` | `LOITERING_VIOLATION` | from event (15) | Stationary / dwelling > 60s in zone |
| `after_hours` | `AFTER_HOURS_ACTIVITY` | from event (10) | Active between 22:00 and 05:00 |
| `unauthorized_vehicle_night`| `UNAUTHORIZED_VEHICLE_AFTER_HOURS` | from event (40) | Vehicle in restricted zone at night |
| `line_crossing` | `LINE_CROSSING` | 20 | Virtual boundary crossing (excluded if direction violation present) |
| `watchlist_vehicle` | `WATCHLIST_MATCH` | 40 | Alert: 1.0 (40), Review: 0.5 (20) |
| `watchlist_person` | `WATCHLIST_MATCH` | 50 | Alert: 1.0 (50), Review: 0.5 (25) |
| `multiple_suspicious` | Bonus rule | +10 | Granted when >= 4 distinct kinds are present |

### Levels

- **LOW:** 0 – 29
- **MEDIUM:** 30 – 59
- **HIGH:** 60 – 79
- **CRITICAL:** 80 – 100

---

## 2. Configuration Reference (`configs/rules.json`)

```json
{
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
    "sources": [ ... ]
  }
}
```

- `max_score`: Ceiling on final threat score (default 100).
- `window_s`: Time horizon in seconds for evidence relevance (default 600s / 10 min).
- `alert_min_score`: Floor score required to trigger any alert (default 10).
- `cooldown_s`: Minimum time between new alert episodes for an entity (default 60s).
- `rearm_s`: Duration score must remain below threshold before re-arming (default 300s).
- `merge_by_plate`: When true, tracks sharing a recognized license plate share threat state.
- `merge_scope`: `camera` (intra-camera) or `global` (inter-camera).
- `excluded_by`: List of higher-precedence sources that suppress this item (prevents double-counting).
- `status_multiplier`: Multipliers for unverified/review-status evidence (default 0.5 for review).

---

## 3. Worked Examples

### Plan Scenario 1: Restricted Area at Night
- Virtual line crossing: +20
- Restricted zone entry: +30
- After-hours movement: +10
- **Total:** $20 + 30 + 10 = 60 ightarrow$ **HIGH (60/100)**
- Escalation path: `LOW` (10) $ightarrow$ `MEDIUM` (40) $ightarrow$ `HIGH` (60)

### Plan Scenario 2: Watchlisted Vehicle in Restricted Zone
- Watchlist vehicle match (alert): +40
- Restricted zone entry: +30
- Unauthorized direction: +20
- After-hours movement: +10
- Virtual line crossing: Excluded by direction violation (+0)
- Distinct kinds count: 4 (Watchlist, Zone, Direction, After-hours) $ightarrow$ Multi-suspicious bonus: +10
- Raw score: $40 + 30 + 20 + 10 + 10 = 110$
- Capped score: $\min(110, 100) = 100 ightarrow$ **CRITICAL (100/100)**

---

## 4. Operational Tools

### Threat Calculator
Test arbitrary evidence combinations and verify scoring logic:
```bash
python scripts/threat_calc.py --plan
python scripts/threat_calc.py watchlist_vehicle:alert zone_violation direction_violation after_hours
```

### Score Replay
Re-evaluate threat scoring with different parameters across recorded runs:
```bash
python scripts/score_replay.py --events ../outputs/runs/<run_id>/events.jsonl --tick 1.0
```

### Configuration Validation
Validate rule definitions, weights, and cross-consistency:
```bash
python scripts/rules_check.py
```

---

## 5. Known Limitations
- Single-camera person tracking does not persist across tracker ID swaps without Re-ID models.
- Asynchronous evidence (ANPR / Watchlist worker threads) may arrive a few frames after raw track creation.
