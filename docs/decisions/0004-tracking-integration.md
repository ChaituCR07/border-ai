# 0004: Multi-Object Tracking Integration via ByteTrack

**Status:** Accepted  
**Date:** 2026-10-05  
**Context:** AI Engine Video Analytics Pipeline (`border-ai`)

---

## Decision

We adopt **ByteTrack** executed as a decoupled, downstream tracking stage immediately following object detection:
1. **Decoupled Architecture:** Tracking runs as a standalone post-detection stage consuming `FrameDetections` and returning `FrameTracks`. We reject coupling detection with tracking inside `model.track()` so that multi-camera batching and model execution remain fully independent.
2. **Per-Camera Isolation:** Each camera owns an isolated `CameraTracker` and `TrackStore`. State, Kalman filter covariances, and track histories are never shared across streams.
3. **Compound Keying:** All objects are indexed globally by `(camera_id, track_id)`.
4. **Two-Stage Detection Floor:** The `Detector` operates at a lowered confidence floor (`detection_conf: 0.25`) for tracking updates. ByteTrack exploits this low-confidence pool in its second association pass to maintain track continuity across partial occlusions and low-contrast silhouettes.
5. **Ultralytics ByteTrack Engine:** Integrated via `ultralytics.trackers.byte_tracker.BYTETracker` (version `8.4.170`).
6. **Class Stability via Lifetime Voting:** Displayed object class labels are derived from confidence-weighted majority voting over the track's lifetime (`dominant_class`), eliminating single-frame classification flicker (e.g. between `car` and `truck`).

---

## Technical Context & Ultralytics 8.4.x Behavior

- **Ultralytics Version:** `8.4.170` (packaged with `lap>=0.5.12` / `lap-0.5.13`).
- **Initialization Interface:** `BYTETracker(args)` accepts an object/namespace containing `track_high_thresh`, `track_low_thresh`, `new_track_thresh`, `track_buffer`, `match_thresh`, and `fuse_score`.
- **Result Format:** Returns an `(N, 8)` ndarray where each row represents `[x1, y1, x2, y2, track_id, score, cls, idx]`.
- **ID Numbering Behavior:** Track IDs increment sequentially within the runtime session. Keying strictly by `(camera_id, track_id)` guarantees namespace separation across cameras.

---

## Selected Default Parameters (`configs/app.yaml`)

- `detection_conf: 0.25`: Provides candidate boxes for ByteTrack second-stage matching.
- `track_high_thresh: 0.50`: Ensures only reliable detections activate new tracks.
- `track_low_thresh: 0.10`: Recovers occluded tracks.
- `new_track_thresh: 0.60`: Suppresses ghost tracks from fleeting noise.
- `track_buffer: 30`: Retains lost tracks for ~1–2 seconds depending on frame rate.
- `match_thresh: 0.80`: Balances permissive spatial association against trajectory swaps.
- `trail_length: 40`: Maintains ground-contact motion history for visualization and Day 6 zone analytics.

---

## Trade-offs & Limitations Accepted

- **Motion-Only Association:** ByteTrack associates detections based on Kalman filter velocity predictions and IoU overlap. It does not extract deep visual appearance embeddings (Re-ID). If an object undergoes prolonged occlusion (> 2–3 seconds) or crosses paths with another similarly sized object, ID switches or fragmentation may occur.
- **Fixed Camera Assumption:** The standard Kalman state equations assume stationary camera viewpoints. Camera jitter or PTZ pan/tilt requires global motion compensation (BoT-SORT), deferred to future optimization.
