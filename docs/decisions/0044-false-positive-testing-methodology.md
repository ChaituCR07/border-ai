# 44. False-Positive Testing Methodology and Evidence Tiers

Date: 2026-11-12
Status: Accepted

## Context

Operational edge surveillance systems suffer from operator fatigue when false-positive rates are unchecked. Previous testing (Days 21-24) focused on positive incident scenario reconciliation, model detection/tracking metrics, ANPR character accuracy, and sustained throughput scaling. However, false positives in operational deployment arise from boundary jitter, perspective distortion, foot-point displacement, vehicle stop-and-go behavior, OCR character confusions on large watchlists, and hours of ordinary, uneventful scene exposure.

Reporting a single naked percentage (e.g. "99% accurate" or "0.1% false alarms") is scientifically meaningless without specifying negative exposure hours, sample size, boundary definition, and confidence intervals. Furthermore, attempting to eliminate false positives by raising detection or rule thresholds risks silencing real threats, violating security objectives.

## Decisions

### 1. Standardized Definitions

Every evaluation, document, and dashboard in BorderVision must adhere to the following terminology:

| Term | Definition |
|---|---|
| **FP event** | A rule-engine event (e.g. `RESTRICTED_ZONE_ENTRY`, `LINE_CROSSING_WRONG_DIRECTION`, `WATCHLIST_HIT`) raised where no ground-truth incident occurred. |
| **FP alert** | An alert generated from rule events of tier $\ge T$ without ground-truth justification. Metrics must report three standard tier cuts: $\ge\text{MEDIUM}$, $\ge\text{HIGH}$, and $\text{CRITICAL}$. |
| **FP rate** | Total FP alerts (or events) divided by **unique camera-hours** of exposure, reported with exact two-sided 95% Poisson confidence intervals: $\left[\lambda_{\text{lo}}, \lambda_{\text{hi}}\right]$ alerts/camera-hour. |
| **Alert precision** | True-Positive alerts $\div$ All generated alerts. Because precision depends strongly on scene incident prevalence, it must always be accompanied by incident sample size $N$ and test footage composition. |
| **Event precision / recall (rule-level)** | Matches between pipeline-produced events and **oracle events** (the same rule engine executed on ground-truth tracks) within a time window of $\pm 1.0\,\text{s}$ for the same spatial subject. |
| **Sensitivity guard** | The mandatory suite of positive test cases (Plan tests 2, 4, 6, scenarios S1/S2, and oracle recall) that must maintain recall $\ge 95\%$ across any false-positive mitigation. |
| **Grey zone** | A documented spatial band around any rule boundary (width = hysteresis deadband margin) where transition behavior is physically indeterminate. Test assertions strictly evaluate *outside the band $\implies$ no alert* and *deep inside $\implies$ alert*. |

### 2. Multi-Tiered Evidence Hierarchy

Evidence is gathered across five distinct, non-overlapping tiers:

```
[Tier A: Logic Tier]            Synthetic tracks + 2D Geometry Oracle -> Real Rule Engine (Boundary / Jitter Properties)
         |
[Tier B: Controlled System]     Plan Tests 1-6 (Negative & Positive Pairs) -> Full Production Stack
         |
[Tier C: Oracle vs System]      GT Tracks vs Tracker Output -> Same Rule Engine (Precision/Recall & Cause Attribution)
         |
[Tier D: Negative Exposure]     Unique Uneventful Footage Hours -> Real Pipeline (Poisson FP Rate per Cam-Hour)
         |
[Tier E: Stress & Perturbation] Synthetic Augmentation (Glare, Shake, Drift, Rain, Noise) -> Brittleness Bounds
```

1. **Tier A (Logic):** Mathematical property-based tests verifying `ZoneEngine`, `LineEngine`, `RuleEngine`, and `ThreatScorer` against an analytical 2D geometry oracle. Evaluates boundary jitter, aspect ratio, perspective height scaling, and frame-rate invariance.
2. **Tier B (Controlled System):** End-to-end evaluation of the 6 canonical plan tests across $\ge 3$ variants each, comparing negative controls against paired positive incident triggers.
3. **Tier C (Oracle vs System):** Directly isolates perception-layer artifacts from rule-logic defects by running ground-truth bounding box tracks alongside DeepSORT/ByteTrack predictions through the identical rule engine.
4. **Tier D (Negative Exposure):** Long-duration execution across hours of verified uneventful footage to establish operational baseline alert frequencies.
5. **Tier E (Stress):** Controlled parameter sweeps across camera translation, rotational drift, illumination drop, glare, and compression artifacts. Reported in a segregated stress table; never pooled into baseline operational exposure.

### 3. Exposure Accounting Rules

1. **Uniqueness:** Only unique, non-overlapping camera footage hours are counted toward exposure. Looping a 5-minute video for 24 hours yields **0.083 camera-hours** of exposure, not 24.
2. **Loop Clustering vs Inflation:** Looped soak runs (such as Day 24 soak testing) are exclusively used to identify recurring spatial false-positive clusters (modulo loop cycle period), not to inflate exposure denominators.
3. **Split Discipline:** Footage is strictly partitioned into development (`dev`) and held-out (`held-out`) partitions prior to any rule or threshold tuning. All headline claims reflect held-out data only.
4. **Zero-Event Bounding:** When zero false positives are observed ($k = 0$), the rate is never reported as "0%". Instead, it must be reported with the exact Poisson one-sided 95% upper bound ($3.689 / \text{exposure\_hours}$) and the Rule of Three ($3.0 / \text{exposure\_hours}$).

### 4. Statistical Rigor

For $k$ observed events over exposure $H$ (in camera-hours) at confidence level $1 - \alpha = 0.95$:
- **Exact Garwood Poisson Interval:**
  $$\lambda_{\text{lo}} = \frac{\chi^2_{2k, \alpha/2}}{2 H}, \quad \lambda_{\text{hi}} = \frac{\chi^2_{2(k+1), 1 - \alpha/2}}{2 H}$$
  For $k = 0$, $\lambda_{\text{lo}} = 0$, and $\lambda_{\text{hi}} = \frac{-\ln(\alpha/2)}{H} \approx \frac{3.688879}{H}$.
- **Wilson Score Interval for Proportions:**
  Used for watchlist match accuracy, rule precision, and recall rates:
  $$w = \frac{p + \frac{z^2}{2n} \pm z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

## Consequences

- All performance reports must declare unique camera-hours derived directly from `docs/testing/exposure_ledger.csv`.
- Bare percentage claims (e.g. "FP rate: 0.2%") are prohibited in documentation and pull requests, enforced by claims audit linting.
- Every negative test must be accompanied by its paired positive counterpart to protect system recall.
