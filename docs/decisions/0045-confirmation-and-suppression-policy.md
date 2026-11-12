# 45. False-Positive Confirmation, Suppression, and Sensitivity Guardrails

Date: 2026-11-12
Status: Accepted

## Context

False positives in computer vision surveillance typically arise from three perception failure modes:
1. Spatial boundary instability (flickering track coordinates jittering across a static zone boundary).
2. Temporal tracking anomalies (track dropouts and ID switches causing reverse directional vectors on counting lines).
3. OCR character confusions (single-frame OCR character substitutions matching a large watchlist).

However, aggressively suppressing false positives by elevating global detector thresholds or expanding exclusion margins inevitably harms system recall, creating dangerous false negatives (missed unauthorized intrusions or watchlisted threats). A disciplined suppression policy must be config-driven, rule-layer gated, and strictly bound to a **sensitivity guard**.

## Decisions

### 1. Mitigation Mechanisms

All mitigations operate as configurable parameters in the rule evaluation and threat scoring pipeline without requiring model re-training:

| Mitigation Mechanism | Architectural Purpose | Config Parameters | Recall Risk & Guard |
|---|---|---|---|
| **Zone Confirmation & Deadband Hysteresis** | Eliminates boundary coordinate jitter and 1-frame boundary flickers. Entry requires the foot-point to remain inside the inner polygon for $\ge N$ consecutive frames; exit requires moving outside the outer polygon. | `confirm_frames`: 3 (120ms at 25fps)<br>`hysteresis_margin`: 0.035 of image width | Delayed alert latency (budget $\le 500\,\text{ms}$). Guarded by Test 2 rapid entry. |
| **Track-Quality Gating** | Suppresses phantom detector noise (foliage, shadows, brief false boxes). Only tracks satisfying age, mean confidence, and spatial scale are forwarded to rule triggers. | `min_hits_for_events`: 3<br>`min_conf_mean`: 0.50<br>`min_box_h_px`: 20.0 | Small/distant persons. Guarded by distant person entry test. |
| **Class Stability Filter** | Prevents animals or vehicles momentarily detected as persons from triggering pedestrian rules. | `dominant_class_window`: 5<br>`min_class_conf`: 0.40 | Brief class transitions. Guarded by vehicle-pedestrian mixed flow. |
| **Line Crossing Debounce & Deduplication** | Prevents stationary vehicle jitter on counting lines and ID-switch double counts during crossing. Requires crossing line segment with side hysteresis, per-track cooldown, and spatial-temporal radius deduplication. | `deadband_px`: 15.0<br>`line_cooldown_s`: 2.0<br>`dedupe_radius_px`: 50.0<br>`dedupe_dt_s`: 1.0 | Fast crossings at low FPS. Guarded by `analytics_fps_min = 5.0`. |
| **Watchlist Corroboration Gating (ADR 0039)** | Exact plate match yields full alert score (+60). Look-alike character matches require consensus agreement ($\ge 2$ reads) or confidence $\ge 0.85$. | `lookalike_confidence_threshold`: 0.85<br>`consensus_min_reads`: 2 | Badly lit watchlisted plates. Guarded by Test 4 night IR plates. |
| **Signal Monotonicity & Cooldown** | Single weak factors (after-hours, permitted crossings) never exceed LOW (< 40). Repeated alerts collapse within cooldown; priority escalation bypasses cooldown. | `cooldown_s`: 60.0<br>`rearm_s`: 120.0<br>`priority_upgrade_bypass`: true | Secondary incidents during cooldown. Mitigated by upgrade bypass. |

### 2. The Sensitivity Guard Protocol

No false-positive mitigation may be merged into production unless the sensitivity guard passes completely:
1. **Plan Tests 2, 4, and 6:** Must achieve 100% detection rate on core positive variants.
2. **Scenario Harness S1 & S2:** Scenarios S1 (Person in Restricted Zone, 60/HIGH) and S2 (Watchlisted Vehicle in Restricted Zone, 80/CRITICAL) must pass 3/3 runs.
3. **Oracle-vs-System Recall:** Rule recall against ground truth oracle tracks must not drop by more than 2.0% absolute compared to pre-mitigation baseline.
4. **Performance Overhead:** The mitigation must add $\le 0.5\,\text{ms}$ processing latency per frame in the Day 24 benchmark harness.

## Consequences

- Mitigations are frozen in `configs/rules.json` and `configs/performance_deployed.json`.
- Ad-hoc threshold adjustments on a per-clip basis are forbidden.
