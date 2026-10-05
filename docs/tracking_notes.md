# Tracking Notes & Evaluation (Day 5)

## 1. Tracking Parameter Sensitivity Sweep

Evaluated across candidate configurations using `scripts/tune_tracker.py` on benchmark footage:

| `det_conf` | `high_thresh` | `match_thresh` | `buffer` | Observations & Trade-offs |
|---|---|---|---|---|
| `0.25` | `0.40` | `0.70` | `30` | Overly strict matching: targets experiencing fast velocity changes fragment into multiple IDs. |
| `0.25` | `0.50` | `0.80` | `30` | **Optimal Baseline:** Balanced association without duplicate tracks or runaway ghost trajectories. |
| `0.25` | `0.50` | `0.80` | `60` | **Extended Occlusion Setting:** Preserves tracks through 2–3s obstacles (e.g. crossing behind vehicles/pillars). |
| `0.40` | `0.50` | `0.80` | `30` | Lacks low-confidence rescue pass; occluded subjects drop and re-initialize with new IDs upon emergence. |

---

## 2. Frame Rate Sensitivity Analysis

Tracking stability relies heavily on frame-to-frame displacement. Low frame rates increase bounding box displacement, causing Kalman predictions to drift and IoU overlap to drop below `match_thresh`.

| Target FPS | Observed Behavior & Track Continuity | Recommendation |
|---|---|---|
| **30 FPS** | Near-zero fragmentation; smooth trajectory trails and continuous ID persistence. | Ideal for high-speed perimeter vehicle gates. |
| **15 FPS** | Stable pedestrian and standard vehicle tracking; minor ghosting on swift motion. | **Standard Production Target** for 3–5 camera streams. |
| **8 FPS** | Noticeable trajectory jitter; fast pedestrians crossing paths trigger ID switches (~2.4x higher fragmentation). | Bare minimum fallback under compute saturation; requires wider `match_thresh` (0.65). |

---

## 3. Manual Error Log & Edge Case Analysis (`crowded.mp4` & `night.mp4`)

| Clip | Timestamp / Frame | Event Type | Old ID → New ID | Underlying Cause | Mitigation Applied |
|---|---|---|---|---|---|
| `crowded.mp4` | 00:08 (F120) | Path Crossing | #4 → #7 | Two pedestrians intersect with overlapping bounding boxes | `match_thresh: 0.8` + confidence weighting |
| `crowded.mp4` | 00:16 (F240) | Occlusion | #3 → #9 | Subject hidden behind stationary vehicle for ~2.5 seconds | `track_buffer: 60` recovers track |
| `night.mp4` | 00:04 (F60) | Missed Detection | N/A | Low contrast illumination prevents detector from meeting `0.25` floor | Upstream sensor/IR lighting required |
| `crowded.mp4` | 00:22 (F330) | Class Jump | `car` ↔ `truck` | Frame-level classification instability | `TrackStore` confidence-weighted majority vote |

---

## 4. Performance & Overhead Summary

- **Tracker Execution Time:** **~0.25 ms per frame** (`BYTETracker.update` + `TrackStore.update`).
- **End-to-End Detect + Track + Render:** ~45–60 ms/frame (CPU host), easily accommodating **> 15 FPS** real-time execution.
