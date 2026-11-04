# ADR 0037: Tracking Evaluation Protocol, MOT17 Sequence Partitioning, and Tuning Policy

## Status
Accepted

## Context
Multi-object tracking is the operational bridge between raw frame detections and high-level behavioral security rules (such as loitering, speed estimation, and line crossing). In tracking benchmarks like MOT17, performance can vary dramatically depending on camera motion (static mounted CCTV vs handheld or vehicle-mounted cameras) and whether the tracker is evaluated in isolation or coupled with a specific detector.

Unregulated hyperparameter tuning across test sequences causes severe data leakage and overfitting, yielding brittle tracking parameters that fail on novel camera installations.

## Decision

1. **Protocol Separation**:
   - **Tracker-Only Protocol**: The tracker is supplied with ground truth detections (or detector detections with frozen confidence), isolating the association, Kalman filter, and trajectory maintenance performance from detector recall limitations.
   - **End-to-End Surveillance Protocol**: Evaluates the coupled detection + tracking pipeline against full ground truth annotations.

2. **Camera-Type Sequence Partitioning**:
   - Primary operational benchmark relies on **Static Camera Sequences** (`MOT17-02`, `MOT17-04`, `MOT17-09`), which accurately mirror pole-mounted border CCTV installations.
   - **Moving Camera Sequences** (`MOT17-05`, `MOT17-10`, `MOT17-11`, `MOT17-13`) are tracked as secondary stress-test benchmarks to assess Kalman filter robustness under camera ego-motion.

3. **Hyperparameter Tuning Policy & Overfitting Prevention**:
   - Hyperparameter exploration (via grid search over `track_high_thresh`, `track_low_thresh`, `match_thresh`, and `track_buffer`) is strictly confined to the `dev_tuning` split (`MOT17-02`, `MOT17-05`).
   - The best candidate parameters are evaluated once on the unseen holdout validation split (`MOT17-09`, `MOT17-11`).
   - Acceptance criterion: The performance degradation on holdout must satisfy $\Delta \text{HOTA} \le 0.02$. If degradation exceeds this margin, the candidate is flagged as overfitted and rejected.
   - Tuned parameters are versioned under `evaluation/configs/tracking_mot17_tuned.json`.

4. **Downstream Alert Impact Quantification**:
   - In addition to academic metrics (HOTA, MOTA, IDF1), the tracking engine is evaluated through an event impact simulator measuring:
     - **Double-Counted Alerts**: Identity switches causing duplicate alarm generation for a single physical intrusion.
     - **Dwell Reset Error**: Track fragmentation interrupting loitering timers and under-reporting loiter durations.
     - **False Tracks / 1,000 frames**: Pure spurious tracks generating false intrusion alarms.

## Consequences
- **Positive**: Prevents test sequence leakage; enforces realistic expectations for fixed-camera border surveillance; links tracking quality directly to alert operator experience.
- **Negative**: Requires maintaining explicit sequence split manifests and running dual-split verification for all tracker configuration changes.
