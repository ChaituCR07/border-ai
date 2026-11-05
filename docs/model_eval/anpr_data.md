# BorderVision-India-ANPR Dataset Specifications & Split Audit

## 1. Overview & Provenance
The **BorderVision-India-ANPR** evaluation corpus comprises field surveillance captures, controlled CCTV gate recordings, and real pass-by sequences collected across Indian border security checkpoints and perimeter access control lanes.

In strict compliance with **ADR 0038** and **ADR 0040**:
- **Vehicle-Disjoint Splits:** Splits are strictly partitioned by `vehicle_id` (never by individual frame/image) to eliminate temporal leakage across video frames.
- **Unreadable Plates Policy:** Severely occluded or physically obliterated plates (unreadable even by human examiners) are tagged `unreadable: true`. They are excluded from OCR character accuracy calculations but **strictly retained** in coverage (read rate) metrics.
- **Privacy Posture:** All third-party raw imagery remains local. Only anonymous metadata, bounding box coordinates, and aggregate metrics are published.

---

## 2. Dataset Composition & Split Summary

| Partition | Total Images | Distinct Vehicles | Cars / SUVs | Two-Wheelers | Commercial (Truck/Bus) | Split Purpose |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Dev Split** | 380 | 80 (40.0%) | 48 | 20 | 12 | Preprocessing ablations, threshold tuning, calibration |
| **Test Split** | 620 | 120 (60.0%) | 74 | 30 | 16 | Formal benchmark claims, CI regression verification |
| **Total Corpus** | **1,000** | **200 (100.0%)** | **122** | **50** | **28** | Full Indian ANPR operational corpus |

---

## 3. Environmental & Condition Breakdown

| Environmental Dimension | Slice Bucket | Share of Dataset (%) | Description |
| :--- | :--- | :---: | :--- |
| **Lighting Condition** | Daytime | 62.0% | Direct sunlight, diffuse daylight, overcast |
| | Low-Light / Dusk | 18.0% | Golden hour, twilight, transitional ambient light |
| | Night (IR Illumination) | 14.0% | 850nm active infrared illuminator on gate post |
| | Night (Unilluminated) | 6.0% | Headlight glare only, ambient sodium/LED lamps |
| **Viewing Angle** | Frontal (0°–15°) | 58.0% | Straight gate entrance approach |
| | Oblique (15°–35°) | 32.0% | Curved access lane or lane shoulder mount |
| | Steep (> 35°) | 10.0% | Elevated 6m mast mounting |
| **Plate Resolution** | > 80 px height | 22.0% | High resolution (close range < 8m) |
| | 50–80 px height | 38.0% | Standard operational zone (8m–15m) |
| | 30–50 px height | 26.0% | Medium range (15m–25m) |
| | 20–30 px height | 10.0% | Long range (25m–35m) |
| | < 20 px height | 4.0% | Sub-operational range (> 35m) |
| **Plate Layout** | Single-line Standard | 78.0% | Standard Indian HSRP / rectangular layout |
| | Two-line Square | 18.0% | Two-wheelers and rear commercial tailgates |
| | Bharat Series (`BH`) | 4.0% | Centralized non-state registration series |
