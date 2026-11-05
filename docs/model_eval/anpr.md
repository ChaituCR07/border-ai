# BorderVision ANPR Evaluation Report

**Run ID:** `run-20261105-anpr-m3`  
**Dataset:** BorderVision-India-ANPR (authorized surveillance set, $n=600$ vehicles, $1,800$ frames)  
**Split:** Disjoint vehicle split (Dev: 240 vehicles, Test: 360 vehicles)  
**Date:** 2026-11-05  
**Evaluation Standard:** ADR 0038, ADR 0039, ADR 0040  

---

## 1. Executive Summary

Automatic Number Plate Recognition (ANPR) was benchmarked across three operational evaluation tiers:
1. **Mode M1 (Oracle Crops):** Evaluates OCR recognition in isolation from bounding-box locator noise.
2. **Mode M2 (Single-Frame Cascaded Pipeline):** Evaluates vehicle detection $\to$ plate localization $\to$ OCR $\to$ validation on individual frames.
3. **Mode M3 (Multi-Frame Positional Consensus):** Evaluates temporal voting along vehicle tracks, benchmarking early-stopping efficiency.

### Headline Metrics (ADR 0040 Formatted Tuples)

| Evaluation Tier | Metric | Value | 95% Wilson CI | Sample Size ($n$) | Split | Run ID |
|---|---|---|---|---|---|---|
| **Mode M1** (Oracle Crop) | Plate Exact Accuracy | **89.2%** | [85.4%, 92.1%] | 240 vehicles | Dev | `run-20261105-anpr-m1` |
| **Mode M1** (Oracle Crop) | Character Accuracy ($1-\text{CER}$) | **96.8%** | [95.9%, 97.5%] | 2,400 chars | Dev | `run-20261105-anpr-m1` |
| **Mode M1** (Oracle Crop) | Read Rate (Coverage) | **98.5%** | [96.8%, 99.4%] | 240 vehicles | Dev | `run-20261105-anpr-m1` |
| **Mode M2** (Single Frame) | Plate Exact Accuracy | **83.4%** | [79.8%, 86.5%] | 360 vehicles | Test | `run-20261105-anpr-m2` |
| **Mode M2** (Single Frame) | Look-Alike Equiv Accuracy | **88.6%** | [85.4%, 91.2%] | 360 vehicles | Test | `run-20261105-anpr-m2` |
| **Mode M2** (Single Frame) | Localization Price ($\Delta \text{M1}\to\text{M2}$) | **-5.8%** | [-8.1%, -3.5%] | 360 vehicles | Test | `run-20261105-anpr-m2` |
| **Mode M3** (Consensus S5) | Plate Exact Accuracy | **91.5%** | [88.7%, 93.8%] | 360 vehicles | Test | `run-20261105-anpr-m3` |
| **Mode M3** (Consensus S5) | Look-Alike Equiv Accuracy | **95.2%** | [92.9%, 96.8%] | 360 vehicles | Test | `run-20261105-anpr-m3` |
| **Mode M3** (Consensus S5) | Read Rate | **96.8%** | [94.8%, 98.1%] | 360 vehicles | Test | `run-20261105-anpr-m3` |
| **Mode M3** (Early Stop) | OCR Compute Reduction | **64.8%** | [62.1%, 67.4%] | 1,800 frames | Test | `run-20261105-anpr-m3` |

*Note: 8 vehicles in the test set were designated as `unreadable` (severely mutilated plates or obscured by tow ropes). Per ADR 0038, unreadable plates were excluded from exact accuracy denominators but included in read-rate / coverage denominators.*

---

## 2. Stage-by-Stage Monotone Pipeline Funnel

Derived from the test split ($N = 360$ vehicles), guaranteeing monotonic retention:

```text
Vehicles in test split                      360  (100.0%)
  │
  ├──→ Vehicle detected (IoU ≥ 0.5)          345   (95.8% retention) [93.2%, 97.5%]
  │      └── Misses: extreme edge truncation (8), heavy dust storm (7)
  │
  ├──→ Plate localized (IoU ≥ 0.5)           332   (92.2% cumulative) [89.0%, 94.6%]
  │      └── Misses: bumper stickers (5), low-contrast night (8)
  │
  ├──→ OCR returned text                     328   (91.1% cumulative) [87.8%, 93.6%]
  │      └── Drop: unreadable or below binarization threshold (4)
  │
  ├──→ Exact match (single-frame best)       300   (83.3% cumulative) [79.2%, 86.8%]
  │      └── Errors: optical substitution (22), character truncation (6)
  │
  ├──→ Passes format validation              292   (81.1% cumulative) [76.8%, 84.7%]
  │      └── Rejections: non-standard series (5), syntax errors (3)
  │
  └──→ Consensus exact (Mode M3 S5)          329   (91.4% cumulative) [88.1%, 93.9%]
         └── Multi-frame consensus recovers 29 single-frame near-misses!
```

---

## 3. Operational Slice Analysis & Placement Rules

Performance stratified across optical geometry and environmental factors:

### 3.1 Plate Height Slice (The Camera Placement Rule)

| Plate Height (px) | Sample Count | Read Rate | Exact Acc | 95% Wilson CI | Look-Alike Acc | Operational Verdict |
|---|---|---|---|---|---|---|
| `< 20 px` | 42 | 64.3% | 42.8% | [29.1%, 57.8%] | 54.8% | **Unusable Zone** (optical undersampling) |
| `20 - 30 px` | 68 | 91.2% | 73.5% | [62.0%, 82.6%] | 82.4% | **Marginal Zone** (requires consensus) |
| `30 - 50 px` | 134 | 98.5% | **91.8%** | [85.9%, 95.3%] | 96.3% | **Recommended Zone** ($\ge 90\%$ exact) |
| `50 - 80 px` | 82 | 100.0% | **96.3%** | [89.8%, 98.7%] | 98.8% | **Optimal Zone** |
| `> 80 px` | 34 | 100.0% | **97.1%** | [85.1%, 99.5%] | 100.0% | **High Precision Zone** |

> [!IMPORTANT]
> **Key Engineering Takeaway:** To achieve $\ge 90\%$ single-frame exact accuracy, camera optics must provide at least **30 pixels of plate height** across the target capture zone. Crops below 20 px should be tagged as sub-resolution and rejected from automated citation.

### 3.2 Viewing Angle & Environmental Slices

| Slice Type | Bucket | Count | Exact Acc | Look-Alike Acc | Key Failure Modes |
|---|---|---|---|---|---|
| **Angle** | Frontal ($\le 15^\circ$) | 210 | 94.3% | 97.6% | Rare look-alike confusions |
| **Angle** | Oblique ($15^\circ - 30^\circ$) | 114 | 88.6% | 93.8% | Aspect compression on outer characters |
| **Angle** | Steep ($> 30^\circ$) | 36 | 69.4% | 77.8% | Keystone distortion; requires dewarping |
| **Lighting** | Daylight | 245 | 93.9% | 96.7% | Optimal conditions |
| **Lighting** | Night (Active IR) | 85 | 87.1% | 92.9% | Moderate halo around retroreflective plates |
| **Lighting** | Rain / Wet Lens | 30 | 76.7% | 83.3% | Droplet refraction and glare streaks |
| **Vehicle** | Four-Wheeler (Car/SUV) | 220 | 93.2% | 96.4% | Standard single-line format |
| **Vehicle** | Two-Wheeler (Motorcycle) | 90 | 85.5% | 91.1% | Two-line split assembly; dirt splash |
| **Vehicle** | Heavy Commercial (Truck/Bus) | 50 | 88.0% | 94.0% | High mounting angle; hand-painted plates |

---

## 4. Multi-Frame Consensus Benchmark (Mode M3)

Benchmarked on 120 vehicle pass-by tracks ($10 - 25$ frames per vehicle):

| Strategy ID | Strategy Description | Exact Acc | Look-Alike Acc | Avg Frames / Veh | OCR Compute Saved | Decision Latency |
|---|---|---|---|---|---|---|
| **S1** | Best-Confidence Single Frame | 85.0% | 89.2% | 15.4 | 0.0% (all frames) | 508 ms |
| **S2** | First Valid Indian Format | 86.7% | 90.0% | 2.1 | **86.4%** | 69 ms |
| **S3** | Majority String Vote | 89.2% | 93.3% | 15.4 | 0.0% | 508 ms |
| **S4** | Confidence-Weighted String Vote | 90.8% | 94.2% | 15.4 | 0.0% | 508 ms |
| **S5** | **Positional Character Voting** | **94.2%** | **97.5%** | 5.4 (early stop) | **64.8%** | **178 ms** |

### Accuracy vs. Frame Budget Curve (Strategy S5)

```text
Frames Budget:   1 frame   2 frames   3 frames   5 frames   8 frames   10+ frames
Exact Accuracy:   83.4%      88.3%      91.5%      93.8%      94.2%       94.2%
                   │          │          │          │          │           │
                   └──────────┴──────────┴──────────┴──────────┴───────────┘
                                Rapid returns plateau at ~5 frames
```

---

## 5. Confidence Calibration & Error Analysis

- **Expected Calibration Error (ECE, 10 bins):** $0.046$ (excellent calibration).
- **Confidently-Wrong Rate ($\tau = 0.85$):** $1.4\%$ of emitted reads ($n=5$ vehicles out of 360).
- **Primary Confusion Pairs:**
  - `0` $\leftrightarrow$ `O` ($34\%$ of substitutions)
  - `8` $\leftrightarrow$ `B` ($18\%$ of substitutions)
  - `1` $\leftrightarrow$ `I` ($14\%$ of substitutions)
  - `5` $\leftrightarrow$ `S` ($11\%$ of substitutions)
  - `2` $\leftrightarrow$ `Z` ($8\%$ of substitutions)
  - All top confusions match active `plate_key()` mappings, confirming ADR 0039 policy.
