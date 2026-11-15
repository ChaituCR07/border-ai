# Border-AI Investigator & Forensic Analysis Guide

This guide describes forensic search, cross-camera journey reconstruction, and evidentiary export workflows for security investigators and compliance officers.

---

## 1. Forensic Plate Search & Look-Alike Matching

The **Investigation Workbench** (`/investigation`) enables rapid retrospective searching across historical sightings:
- **Exact Plate Search:** Enter standard vehicle plates (e.g. `KA01AB1234`).
- **Phonetic & Look-Alike Search (ADR 0023):** Enable the **Look-Alike Mode** checkbox. The system queries the database using Levenshtein distance weighted by optical OCR character substitution costs (`B/8`, `O/0`, `1/I`, `S/5`, `Z/2`). This surfaces target vehicles even when lens glare or mud distorted a character during capture.
- **Faceted Filters:** Filter by camera zone, object class (truck, car, motorcycle), date range, and minimum threat score tier.

---

## 2. Cross-Camera Journey Reconstruction

When an investigator selects a vehicle sighting, the system automatically correlates adjacent observations across camera topology nodes:
1. **Interactive Journey Map:**
   - Visualizes the vehicle's spatial progression across the physical facility: `CAM-01 (Gate 1)` $\to$ `CAM-02 (Perimeter)` $\to$ `CAM-04 (Restricted Depot)`.
2. **Transit Time & Velocity Plausibility:**
   - Displays inter-camera transit times (e.g. `10:02:14` at CAM-01 $\to$ `10:08:30` at CAM-02 $\to$ $\Delta t = 6\text{m } 16\text{s}$).
   - Compares elapsed time against configured topology bounds (`min_transit_s`, `max_transit_s`).
3. **Anomaly Flags (Impossible Speed):**
   - If the same license plate appears simultaneously at two distant cameras faster than physically possible, the platform flags the journey with an `IMPOSSIBLE_SPEED` warning badge (indicating plate cloning or counterfeit plates).

---

## 3. Forensic Evidence Export

1. Click **`[Export CSV]`** on the investigation toolbar.
2. Select desired date ranges and metadata fields (event timestamps, camera IDs, OCR confidence scores, threat scores).
3. The platform generates an auditable, timestamped CSV package (`journey_<plate>_<timestamp>.csv`) and records the export action in `api_audit_log` with the investigator's account identity.
