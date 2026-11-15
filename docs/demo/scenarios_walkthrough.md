# Border-AI Demonstration Scenarios Walkthrough

This guide details the three core demonstration scenarios showcased in the Border-AI final video and live demonstrations.

---

## Scenario 1: Unauthorized Perimeter Intrusion (Score 60, HIGH)

### Objective
Demonstrate multi-signal spatial and temporal threat correlation resulting in an explainable High-Priority alert.

### Step-by-Step Walkthrough
1. **Camera Feed:** `CAM-001 (North Perimeter)`.
2. **Actor Action:** A pedestrian approaches the facility perimeter after 22:00 UTC. The pedestrian traverses the virtual tripwire `Line-North-01` in the `ingress` direction and enters the restricted boundary `Zone-Perimeter-North`.
3. **Engine Evaluation:**
   - Detects person class (YOLOv8s, confidence 0.88).
   - ByteTrack maintains track ID `TRK-104`.
   - Spatial engine triggers `LINE_CROSSING` (+20 points) and `ZONE_VIOLATION` (+30 points).
   - Temporal engine checks clock (`02:13:00` UTC) and triggers `AFTER_HOURS` (+10 points).
4. **Calculated Threat Score:** $30 + 20 + 10 = \mathbf{60 / 100}$ ($\to \text{HIGH}$ severity tier).
5. **Operator View:**
   - Yellow alert toast appears: *"HIGH (60/100): Unauthorized Perimeter Intrusion"*.
   - Factor checklist displays 3 verified contributions with exact point weights.
   - Operator clicks `[ACKNOWLEDGE]`.

---

## Scenario 2: Stolen Watchlist Vehicle Breach (Score 80, CRITICAL)

### Objective
Demonstrate real-time ANPR license plate consensus, database watchlist hit, transactional email outbox dispatch, and single-winner acknowledgement.

### Step-by-Step Walkthrough
1. **Camera Feed:** `CAM-002 (Main Ingress Gate)`.
2. **Actor Action:** Vehicle approaches gate checkpoint. License plate `KA01AB1234` enters camera field of view.
3. **Engine Evaluation:**
   - ANPR extracts plate crop; PaddleOCR PP-OCRv6 performs multi-frame voting (5 frames, 99.2% OCR confidence).
   - Watchlist engine matches plate against `watchlist_vehicles` (Reason: Stolen Vehicle Report #CR-2026-881).
   - Rules R001 (Restricted Zone +30), R004 (After-Hours +10), and R005 (Watchlist Vehicle +40) fire.
4. **Calculated Threat Score:** $40 + 30 + 10 = \mathbf{80 / 100}$ ($\to \text{CRITICAL}$ severity tier).
5. **Operator & Notification Actions:**
   - Pulsing red banner and audio chime trigger across all operator dashboards in $<50\text{ms}$.
   - Transactional outbox service captures pre-annotation evidence JPEG and dispatches formatted HTML email via SMTP to security dispatch.
   - Operator clicks `[ACKNOWLEDGE]`. Database row updates atomically; all secondary consoles immediately show the incident acknowledged.

---

## Scenario 3: Forensic Journey Reconstruction & Anomaly Detection

### Objective
Demonstrate retrospective search across camera topologies, speed plausibility validation, and impossible-travel anomaly detection.

### Step-by-Step Walkthrough
1. **Navigate to Workbench:** Open `/investigation`.
2. **Search Criteria:** Enter license plate `KA01AB1234` with **Look-Alike Mode** enabled.
3. **Sighting Timeline:** The workbench surfaces sightings across three distinct camera nodes:
   - `CAM-001 (North Gate)`: Detected at `10:02:14` UTC.
   - `CAM-002 (Perimeter Road)`: Detected at `10:08:30` UTC ($\Delta t = 6\text{m } 16\text{s}$, transit speed plausible: $24\text{ km/h}$).
   - `CAM-004 (Secure Logistics Bay)`: Detected at `10:15:45` UTC.
4. **Anomaly Demonstration (Plate Cloning):**
   - Inject synthetic second sighting at `CAM-005 (South Gate)` at `10:09:00` UTC ($30\text{ seconds}$ after CAM-002 sighting, physical distance $5\text{ km}$).
   - Platform automatically highlights the journey segment in orange and attaches an **`IMPOSSIBLE_SPEED`** anomaly badge, alerting investigators to potential fraudulent cloned plates.
