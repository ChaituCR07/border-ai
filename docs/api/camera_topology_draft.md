# Camera Topology Draft (Demo Layout)

## Overview
This document defines the schematic physical layout, interconnecting road links, and baseline transit durations for the demo checkpoint environment.

## 1. Camera Nodes

| Camera ID | Name | Coordinates (X, Y) | Role |
|---|---|---|---|
| **CAM-01** | North Perimeter Highway | (10.0, 55.0) | Entry highway approach |
| **CAM-02** | Checkpoint Outer Approach | (32.0, 55.0) | Main feeder intersection |
| **CAM-03** | Service Road Bypass | (52.0, 25.0) | Unpaved bypass / inspection loop |
| **CAM-04** | Primary Checkpoint Gate | (68.0, 50.0) | Main toll and inspection lane |
| **CAM-05** | Restricted Facility Corridor | (90.0, 40.0) | Inner secure compound gate |

## 2. Interconnecting Links

| Segment | Direction | Min Transit (s) | Typical Transit (s) | Max Transit (s) | Overlap | Notes |
|---|---|---|---|---|---|---|
| **CAM-01 ↔ CAM-02** | Both | 240 (4m) | 360 (6m) | 600 (10m) | No | Main highway link |
| **CAM-02 ↔ CAM-03** | Both | 90 (1.5m) | 150 (2.5m) | 300 (5m) | No | Turnoff into service bypass |
| **CAM-03 ↔ CAM-04** | Both | 15 (0.25m) | 30 (0.5m) | 90 (1.5m) | No | Service road rejoin |
| **CAM-02 ↔ CAM-04** | Both | 300 (5m) | 420 (7m) | 720 (12m) | No | Direct main road |
| **CAM-04 ↔ CAM-05** | Both | 40 (0.66m) | 70 (1.16m) | 180 (3m) | No | Access lane to restricted zone |

## 3. Route Scenarios

- **Scenario 3 (Direct Highway & Main Road):**
  `CAM-01 → CAM-02 → CAM-04`
  - Gap 1 (01 → 02): 360 s (Typical, Plausible)
  - Gap 2 (02 → 04): 420 s (Typical, Plausible)
  - Total time: ~780 s (~13 min)

- **Day 18 Acceptance Scenario (Bypass Route):**
  `CAM-03 → CAM-04 → CAM-05`
  - Gap 1 (03 → 04): 28 s (Typical ~30 s, Plausible)
  - Gap 2 (04 → 05): 72 s (Typical ~70 s, Plausible)

- **Missed Camera Detection:**
  `CAM-02 → CAM-04` in 178 s:
  - Direct road min is 300 s (too fast for direct road).
  - Route via CAM-03 has min $90 + 15 = 105$ s and max $300 + 90 = 390$ s.
  - Since 178 s is consistent only with the route via CAM-03, `missed_cameras` reports `["CAM-03"]`.
