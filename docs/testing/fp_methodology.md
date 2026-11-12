# False-Positive Testing Methodology and Measurement Specification

**Project:** Border-AI Video Intelligence Platform  
**Document Status:** FROZEN prior to evaluation runs  
**Associated ADRs:** ADR 0044, ADR 0045, ADR 0046  

---

## 1. Overview and Metric Definitions

False-positive rates must reflect operational reality rather than synthetic cherry-picking. This document registers all frozen test geometries, dataset splits, target alert-fatigue thresholds, and statistical estimation methods.

### 1.1 Defined Quantities

- **FP Event:** An atomic rule evaluation trigger (such as `RESTRICTED_ZONE_ENTRY`, `LINE_CROSSING_WRONG_DIRECTION`, or `WATCHLIST_HIT`) that has no corresponding ground-truth event.
- **FP Alert:** An incident alert emitted by the event aggregator / threat scorer with tier $\ge T$. Evaluated at:
  - $\ge\text{MEDIUM}$ (threat score $\ge 40$)
  - $\ge\text{HIGH}$ (threat score $\ge 60$)
  - $\text{CRITICAL}$ (threat score $\ge 80$)
- **FP Rate:** $\lambda = \frac{k}{H}$ alerts per camera-hour, where $k$ is total observed false alerts and $H$ is unique non-looped exposure hours.
- **Poisson 95% Confidence Interval:** Exact Garwood interval $[\lambda_{\text{lo}}, \lambda_{\text{hi}}]$. For $k = 0$, upper bound is $\frac{3.689}{H}$.
- **Sensitivity Guard:** Core positive test cases (Plan tests 2, 4, 6 and Day 21 scenarios S1, S2) must sustain $\ge 95\%$ recall (3/3 for deterministic scenarios) across all evaluated mitigations.
- **Grey Zone:** Spatial transition zone with width equal to $2 \times \text{hysteresis\_margin}$ where rule state transitions are physically undefined.

---

## 2. Alert-Fatigue Design Targets (Frozen)

| Metric | Target | Verification Method |
|---|---|---|
| **Plan Tests 1–6 (Core variants)** | 100% pass (6/6 pairs) | Automated spec runner × 3 runs |
| **Logic-Tier Property Tests** | 100% pass across all seeds | Hypothesis-style property suite (200 cases/prop) |
| **FP Alerts $\ge\text{HIGH}$ (Normal Footage)** | $\le 0.10$ per camera-hour | Negative exposure runs with Poisson CI |
| **FP Alerts $\text{CRITICAL}$ (Normal Footage)** | $\le 0.01$ per camera-hour | Negative exposure runs (upper bound reported) |
| **Rule-Level Precision vs Oracle (Static)** | $\ge 0.90$ with recall $\ge 0.90$ | Oracle-vs-system replay matching ($\pm 1.0\,\text{s}$) |
| **Watchlist False Matches** | $\le 1.0$ per 1,000 reads | Empirical sampling on 100-plate list |
| **Alert Burstiness** | $\le 3$ alerts/min per camera | Cooldown/rearm collapse validation |
| **Sensitivity Guard** | $\ge 95\%$ positive case retention | Automated guard regression suite |

---

## 3. Test Geometry Register

The following scene geometries are registered and frozen before evaluating test footage. **No geometries may be modified post-test to fit observed results.**

```
+-----------------------------------------------------------------------+
| CAM-01: Perimeter Fence (1280x720)                                   |
| Polygon: [(0.15, 0.40), (0.85, 0.40), (0.85, 0.95), (0.15, 0.95)]    |
| Deadband Hysteresis Margin: 0.035 (45px at 1280w)                     |
| Confirmation Window: 3 frames (120ms at 25fps)                        |
+-----------------------------------------------------------------------+
| CAM-02: Checkpoint Access Gate (1280x720)                            |
| Counting Line: P1=(0.20, 0.65), P2=(0.80, 0.65)                      |
| Permitted Direction: SOUTH (+1, downwards in image space)            |
| Wrong Direction: NORTH (-1, upwards in image space)                  |
| Deadband Hysteresis Band: 0.025 (32px at 1280w)                       |
| Line Debounce Cooldown: 1.5 seconds                                   |
+-----------------------------------------------------------------------+
| CAM-03: Restricted Loading Bay (1920x1080)                            |
| Polygon: [(0.30, 0.25), (0.75, 0.25), (0.80, 0.85), (0.25, 0.85)]    |
| Deadband Margin: 0.030 (58px at 1920w)                                |
+-----------------------------------------------------------------------+
| CAM-04: Exit Lane (1920x1080)                                         |
| Counting Line: P1=(0.10, 0.50), P2=(0.90, 0.50)                      |
| Permitted Direction: NORTH (-1, downwards out of gate)                |
+-----------------------------------------------------------------------+
```

---

## 4. Dataset Splits and Exposure Plan

All recordings and video sources are partitioned into disjoint sets prior to any rule parameter tuning.

| Dataset Source | Modality | Dev Clips (Tuning) | Held-Out Clips (Reporting) | Total Unique Hours | License |
|---|---|---|---|---:|---|
| **BorderVision Own Static** | Perimeter & Gate | `cam01_dev_01..03.mp4`, `cam02_dev_01..02.mp4` | `cam01_eval_01..06.mp4`, `cam02_eval_01..05.mp4` | 3.50 h | Proprietary / Internal |
| **MOT17 Static Sequences** | Pedestrian Walkway | `MOT17-02-FRCNN` | `MOT17-04-FRCNN`, `MOT17-09-FRCNN` | 0.25 h | CC BY-NC-SA 4.0 |
| **Traffic Flow Benchmark** | Vehicle Line Crossing | Sequences 01..10 | Sequences 11..25 | 2.25 h | Research / Academic |
| **Total Exposure** | Multi-Scene | **2.00 h** | **4.25 h** | **6.25 h** | Verified Unique |

---

## 5. Tier Aggregation and Triage Protocol

1. Every alert produced during test runs is recorded with its timestamp, camera ID, threat score, and tier.
2. Unmatched alerts are categorized in `docs/testing/fp_log.csv` against the closed cause taxonomy.
3. If an alert is determined to be a genuine event missed by initial labeling, it is tagged as `gt_error=yes` and excluded from false-positive counts upon review.
