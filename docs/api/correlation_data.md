# Correlation Data Audit

## 1. Plate-less Sightings & Data Audit
- **Vehicle Event Composition:** In typical surveillance feeds, approximately 25%–35% of raw vehicle detections have unreadable, obscured, or out-of-frame license plates.
- **Correlation Boundary:** Correlation across cameras requires an identifying token (`plate_key` or `vehicle_id`). Plate-less sightings cannot be correlated automatically and remain isolated to their respective camera timeline.
- **Honest Framing:** The UI clearly notes: *"Correlated by plate. Unread or plate-less vehicle passes cannot be tracked across cameras."*

## 2. Vehicle Merging Reliability
- In the Day 14 relational model, the `vehicles` table stores merged tracks per recognized license plate within a camera stream.
- Different physical cameras produce distinct track IDs and local vehicle records. Cross-camera correlation must rely primarily on `plate_norm` and `plate_key` rather than expecting a single shared synthetic `vehicle_id` across disparate edge devices.
- Searching by `vehicle_id` operates within-camera or across federated multi-camera nodes that synchronize track states.

## 3. Appearance Factor Candidate Fields
Future multi-factor appearance scoring (ADR 0026 stretch) can evaluate:
- `metadata.vehicle_class` (`car`, `truck`, `bus`, `motorcycle`)
- `metadata.color` (dominant HSV color cluster)
- `metadata.reid_candidate_id` / `metadata.reid_similarity` (ColorLayout / appearance embedding from Day 10)

## 4. Camera Inventory & Schematic Map Coordinates
For schematic SVG visualization without external map tiles, cameras are mapped to a 0–100 coordinate plane:
- **CAM-01:** Highway Entrance / North (`map_x: 10`, `map_y: 55`)
- **CAM-02:** Approach Gate West (`map_x: 32`, `map_y: 55`)
- **CAM-03:** Service Road Bypass (`map_x: 52`, `map_y: 25`)
- **CAM-04:** Checkpoint Alpha (`map_x: 68`, `map_y: 50`)
- **CAM-05:** Restricted Corridor South (`map_x: 90`, `map_y: 40`)

## 5. Clock Synchronization (NTP)
- All cameras and edge capture nodes are assumed to synchronize with a common NTP time source (UTC).
- To protect against sub-second network jitter or clock drift, `speed_tolerance: 0.8` provides a 20% tolerance band before flagging a hop as `IMPOSSIBLE_TRAVEL`.

## 6. Event to Sighting Mapping
- Events with a non-empty `plate` (`plate_number` or `metadata->>'plate'`) or `vehicle_id` qualify as sightings.
- Consecutive events on the same camera within 120 seconds are consolidated into a single `Sighting` entry with `first_seen`, `last_seen`, `event_count`, `max_score`, and unique plate variants seen.

