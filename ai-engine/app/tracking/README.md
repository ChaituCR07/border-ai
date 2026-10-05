# Multi-Object Tracking Engine (`app/tracking`)

## 1. Overview
The tracking module provides persistent identification (`track_id`), trajectory trail maintenance, and lifecycle tracking for objects across continuous video streams. It uses **ByteTrack** for spatial-temporal association and **TrackStore** for state management and temporal class stability.

---

## 2. Key Architecture & Components

```text
                     FrameDetections (conf >= 0.25)
                                  ↓
                        [ CameraTracker ]
                      (Ultralytics ByteTrack)
                                  ↓
                        TrackedObject List
                                  ↓
                         [ TrackStore ]
          ├── State Machine: ACTIVE → LOST → REMOVED
          ├── Trajectory History: Deque of (timestamp, x, y)
          ├── Class Voting: Confidence-weighted majority vote
          └── Lifecycle Events: TrackUpdate (new, lost, reactivated, removed)
                                  ↓
                       FrameTracks (JSON Contract)
```

### Components:
- **`tracker.py` (`CameraTracker`)**: Wraps ByteTrack. Operates with a two-stage association pipeline:
  1. High-confidence detections (`conf >= 0.50`) are matched against existing Kalman filter tracks via IoU overlap.
  2. Unmatched tracks are matched against low-confidence detections (`0.10 <= conf < 0.50`) to rescue partially occluded objects.
- **`track_store.py` (`TrackStore`)**: Maintains ground-truth tracking state for a single camera, tracks duration, displacement, and majority-voted class labels.
- **`manager.py` (`MultiCameraTracker`)**: Manages isolated tracking instances across multiple streams, ensuring strict `(camera_id, track_id)` key isolation.
- **`metrics.py`**: Computes tracking health metrics: total tracks, short tracks (< 1s), average/median durations, and candidate fragmentations.

---

## 3. Track Lifecycle State Machine

- **`ACTIVE`**: The object is currently visible and matched in the current frame.
- **`LOST`**: The object was not matched in the current frame but has been lost for fewer than `max_lost_frames` (kept in memory).
- **`REACTIVATED`**: A lost track successfully re-associated with a candidate detection within its buffer window.
- **`REMOVED`**: A track lost for longer than `max_lost_frames` is evicted from active memory into the bounded `finished` archive.

---

## 4. Configuration Parameters (`configs/app.yaml`)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `detection_conf` | float | `0.25` | Detector confidence floor fed to tracking |
| `track_high_thresh` | float | `0.50` | Minimum score to start or continue tracks in stage 1 |
| `track_low_thresh` | float | `0.10` | Low-score floor for occlusion rescue in stage 2 |
| `new_track_thresh` | float | `0.60` | Minimum score required to initialize a new track |
| `track_buffer` | int | `30` | Frames to keep lost tracks (scaled to camera FPS) |
| `match_thresh` | float | `0.80` | IoU association threshold |
| `fuse_score` | bool | `true` | Combine detection confidence with IoU score |
| `trail_length` | int | `40` | Maximum points retained in ground-contact trail |
