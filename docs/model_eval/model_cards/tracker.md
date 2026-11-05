# Model Card: BorderVision Multi-Object Tracker

## 1. Model Details
- **Model Name:** BorderVision Multi-Object Tracker
- **Architecture:** ByteTrack (association with Kalman filter state estimation and dual-threshold matching)
- **Primary Task:** Multi-object tracking (MOT) across video frames
- **Version:** v1.0.0
- **Release Date:** 2026-11-04
- **Licence:** MIT (ByteTrack)
- **Citations:** Zhang et al. (2022), *ByteTrack: Multi-Object Tracking by Associating Every Detection Box*

## 2. Intended Use & Out-of-Scope Use
- **Intended Use:**
  - Establishing continuous trajectories for moving vehicles and pedestrians.
  - Feeding trajectory histories to loitering, speed calculation, and line-crossing alert engines.
  - Multi-frame consensus aggregation for ANPR reads along a vehicle track.
- **Out-of-Scope Use:**
  - Re-identifying subjects across non-overlapping camera networks (cross-camera Re-ID is handled by separate prototype models).
  - Biometric recognition or long-term behavioral profiling outside active camera sessions.

## 3. Factors & Environmental Conditions
- **Camera Types:** Primary optimization on **static pole-mounted CCTV** (per ADR 0037). Functional on slow pan-tilt-zoom (PTZ) cameras; not intended for high-jitter handheld bodycams.
- **Frame Rate:** Optimal at $15 - 30\,\text{FPS}$. Lower frame rates ($<10\,\text{FPS}$) degrade Kalman filter velocity predictions during sharp turns.

## 4. Benchmark Metrics & Operating Points
- **Static Surveillance Sequence Benchmark (MOT17 Static CCTV Split: `MOT17-02`, `MOT17-04`, `MOT17-09`):**
  - **HOTA:** $68.4\%$ $[66.1\%, 70.6\%]$ ($n=3$ full sequences, $2,650$ tracks, run `run-20261104-track-eval-01`, 2026-11-04).
  - **MOTA:** $72.1\%$ $[69.8\%, 74.3\%]$.
  - **IDF1:** $74.5\%$ $[72.0\%, 76.8\%]$.
  - **ID Switches / 1,000 frames:** $4.2$ switches.
- **Event Impact Metrics:**
  - **Duplicate Alert Rate:** $0.8\%$ of vehicle crossings.
  - **Dwell Reset Error:** $< 1.2\,\text{seconds}$ on $30\,\text{second}$ loiter events.
- **Tuned Hyperparameters (`evaluation/configs/tracking_mot17_tuned.json`):**
  - `track_high_thresh`: $0.50$
  - `track_low_thresh`: $0.15$
  - `match_thresh`: $0.75$
  - `track_buffer`: $30$ frames

## 5. Evaluation Data
- **MOT17 Benchmark:** Evaluated according to ADR 0037 sequence partitioning policy (static cameras prioritized; moving cameras segregated to assess ego-motion resilience).
- **BorderVision Local Pass-By Track Set:** 24 vehicle tracks capturing entry, queuing, and exit at test gates.

## 6. Ethical Considerations & Privacy Risks
- Tracks are ephemeral and assigned randomized UUIDs.
- Once a target exits the field of view and the `track_buffer` expires, track state is permanently unlinked.

## 7. Operational Recommendations
- Maintain constant frame intervals ($33\,\text{ms}$ or $66\,\text{ms}$); dropouts exceeding 15 consecutive frames will cause track fragmentation and ID resets.
