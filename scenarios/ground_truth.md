# Scenario Ground Truth Catalog

This document defines the key events, expected timestamps, and scoring criteria for acceptance scenarios S0 through S3.

---

## Scenario S0: Normal Traffic (Negative Control)
- **Camera:** CAM-01
- **Footage:** `footage/camera_01/normal.mp4`
- **Expected Outcome:** Zero threat alerts (score <= 29), zero notification emails, all tracks normal.

---

## Scenario S1: Restricted Zone Night Intrusion
- **Camera:** CAM-01
- **Footage:** `footage/camera_01/restricted_zone.mp4`
- **Ground Truth Timeline:**
  - `00:08.5`: Person approaches perimeter fence.
  - `00:12.4`: Line crossing event detected across perimeter boundary (+20 pts).
  - `00:15.1`: Subject enters restricted border staging zone (+30 pts).
  - After-hours active time window (+10 pts).
- **Threat Score Calculation:** 20 + 30 + 10 = **60 pts (HIGH priority)**.
- **Expected Alert:** Exactly one HIGH priority alert at CAM-01.

---

## Scenario S2: Watchlisted Vehicle Intrusion
- **Camera:** CAM-02
- **Footage:** `footage/camera_02/watchlist.mp4`
- **Ground Truth Timeline:**
  - `00:04.2`: Vehicle enters camera FOV.
  - `00:06.8`: Plate KA01AB1234 recognized by ANPR consensus OCR engine.
  - `00:07.1`: Watchlist hit identified (+40 pts).
  - `00:11.3`: Vehicle crosses into restricted gate access zone (+30 pts).
  - After-hours rule active (+10 pts).
- **Threat Score Calculation:** 40 + 30 + 10 = **80 pts (CRITICAL priority)**.
- **Expected Alert:** Exactly one CRITICAL priority alert, instant email dispatched with snapshot image.
