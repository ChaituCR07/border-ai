# Cross-Camera Correlation Operator & Investigator Guide

## 1. Overview
The Cross-Camera Correlation Engine transforms chronological license-plate detections into physically plausible vehicle journeys. Using the schematic camera network topology, it evaluates transit times between checkpoints, detects physical impossibilities, clusters multi-day trips, and flags anomalies (such as cloned license plates and missed checkpoints).

---

## 2. Reading the Schematic Journey Map & Link Chips

### 2.1 The Schematic Map
- **Nodes:** Physical camera checkpoints positioned on a 0–100 coordinate grid.
- **Numbered Stops (①, ②, ③):** Checkpoints visited in chronological order along the active trajectory.
- **Thick Colored Edges:** Directed transit paths between consecutive sightings.
- **Faint Dashed Edges:** Underlying roadway topology connections.
- **Muted Gray Nodes:** Checkpoints in the network not visited during this journey.
- **Hollow Yellow Nodes (`?`):** Missed camera checkpoints (expected along every consistent route between checkpoints $A$ and $B$, but where no sighting was recorded).

### 2.2 Link Plausibility Classes & Styling
Every cross-camera hop is evaluated into one of eight plausibility classes. Styling uses distinct colors, icons, and dash patterns to ensure clarity in all viewing conditions:

| Class | Icon | Pattern | Meaning |
|---|---|---|---|
| `PLAUSIBLE` | ✓ | Solid Green | Transit time is within the expected roadway bounds (`min_s` to `max_s`). |
| `FAST` | ⚠ | Dashed Amber | Transit time is slightly faster than typical minimum, but within speed tolerance. |
| `SLOW` | ⚠ | Dashed Amber | Transit time exceeded the expected roadway maximum (e.g. vehicle stopped or diverted). |
| `IMPOSSIBLE` | ✕ | Dotted Red | Sighting occurred far faster than the fastest possible route. |
| `SIMULTANEOUS` | ✕ | Dotted Red | Vehicle sighted at another location before departing the previous camera (non-overlapping). |
| `OVERLAP_OK` | ✓ | Solid Green | Overlapping fields of view between adjacent cameras. |
| `REVISIT` | ↺ | Solid Green | Returned to the same checkpoint. |
| `UNLINKED` | ? | Dotted Gray | Traversed between cameras with no defined roadway link in the topology. |

### 2.3 Confidence Factors
Clicking or focusing any `LinkChip` reveals the breakdown:
- **Plate Factor:** `100%` for identical OCR reads; `70%` for look-alike OCR variants (e.g. `B` vs `8`, `I` vs `1`).
- **Timing Factor:** `100%` within typical travel band; `70%` within range; `50%` for fast transits; `40%–60%` for slow transits.
- **Expected Range:** Expected travel window (`min_s` to `max_s`, typical `typical_s`).
- **Missed Cameras:** Any intermediate cameras expected on all consistent routes that saw nothing.

---

## 3. Investigating Anomalies

### 3.1 `IMPOSSIBLE_TRAVEL` & `MULTIPLE_TRAJECTORIES`
- **What it means:** The same license plate was detected at two distant cameras within a timeframe that is physically impossible to traverse.
- **Investigative action:**
  - Check the warning banner: *"This plate appears on N incompatible trajectories — possible duplicated plate or misread. This is a lead, not a conclusion."*
  - Compare snapshot imagery on Trajectory `[T1]` and `[T2]`. Verify vehicle make, model, and color.
  - If vehicle appearances differ: likely a cloned license plate or an ANPR OCR misread.
  - If appearances match: investigate potential clock desynchronization or emergency speed bypass.

### 3.2 `MISSED_CAMERA`
- **What it means:** Every topologically feasible route between camera $A$ and camera $B$ passes through checkpoint $X$, but checkpoint $X$ recorded no sighting.
- **Investigative action:**
  - Verify whether camera $X$ had an offline period or obscured sensor.
  - Inspect whether an unmapped dirt track, bypass road, or off-road trail exists between $A$ and $B$.

---

## 4. Path Pattern (Sequence) Search

### 4.1 When to Use Sequence Search
Sequence search allows an Investigator or Admin to answer:
*"Which vehicles passed CAM-01, then CAM-02, then CAM-04 within 15 minutes of each other?"*

### 4.2 Governance & Mandatory Purpose
- **Restricted Access:** Investigator and Admin roles only.
- **Operational Purpose:** A descriptive purpose ($\ge 5$ characters) is legally required. All searches are recorded in the immutable `api_audit_log`.
- **Parameters:**
  - 2 to 5 ordered camera steps.
  - Time window up to 7 days.
  - Max hop gap (`max_hop_gap_s`, default 900 s).
  - Results capped at 50 plate clusters.

---

## 5. Limitations & Caveats
1. **Appearance Matching:** Appearance embeddings are not yet active in this version; correlation relies on plate strings and topology.
2. **Clock Synchronization:** All cameras are assumed to be synchronized via NTP.
3. **Legal Lead Status:** Trajectories and anomaly alerts are investigative leads to guide human operators, not automated legal proof. Visual verification remains required.
