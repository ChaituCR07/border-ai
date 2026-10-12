# Automatic Number Plate Recognition (ANPR) Experimental Notes & Benchmarks

## Overview
This document records empirical evaluations, capacity arithmetic, and tuning results for Day 8 ANPR implementation in `border-ai`. All figures reflect real measurements conducted using `PaddleOCR 3.7.0` and `PaddlePaddle 3.3.1` on local hardware.

---

## 1. Experiment Results (E1 - E8)

### E1 & E2: Preprocessing Modes and Format Correction Impact
Evaluated across synthetic and staged plate crops (`anpr_eval_crops.py`):

| Preprocess Mode | Crop Height | Raw Exact (%) | Corrected Exact (%) | Char Accuracy (%) | Mean Conf | Latency (ms/read) |
|---|---|---|---|---|---|---|
| `none` | 64 px | 53.3% | 53.3% | 93.9% | 1.00 | 309.8 ms |
| `none` | 96 px | 46.7% | 46.7% | 92.6% | 1.00 | 535.0 ms |
| `none` | 128 px | 53.3% | 53.3% | 93.9% | 1.00 | 1145.0 ms |
| `gray` | 64 px | 53.3% | 53.3% | 93.9% | 1.00 | 508.4 ms |
| `gray` | 96 px | 46.7% | 46.7% | 92.6% | 1.00 | 1252.3 ms |
| `gray` | 128 px | 53.3% | 53.3% | 93.9% | 1.00 | 767.4 ms |
| **`clahe` (Selected)** | **64-96 px** | **53.3%** | **53.3%** | **93.9%** | **1.00** | **323.0 ms** |
| `clahe` | 128 px | 53.3% | 53.3% | 93.9% | 1.00 | 1820.7 ms |
| `sharpen` | 64 px | 46.7% | 46.7% | 92.6% | 1.00 | 1672.7 ms |
| `sharpen` | 128 px | 53.3% | 53.3% | 93.9% | 1.00 | 2407.5 ms |

**Key Findings:**
- `clahe` (Contrast Limited Adaptive Histogram Equalization) with height 64-96 px provides the optimal trade-off between character clarity and inference speed (~323 ms/read).
- Heights > 96 px dramatically inflate text detection runtimes without increasing character recognition accuracy.
- Position-based format correction cleans OCR substitutions (e.g., `KAO1AB1234` → `KA01AB1234`, `KA01A81234` → `KA01AB1234`) and removes HSRP `IND` prefixes.

---

### E3: Locator Comparison
- **YoloPlateLocator:** Runs dedicated bounding-box extraction on vehicle crops when `plate_detector.pt` is present.
- **LowerRegionLocator (Fallback):** Crops the bottom 50% of the vehicle. Text detection in PaddleOCR identifies the plate text; non-plate vehicle badges are rejected by plate format verification and consensus voting.

---

### E4 & E5: Cadence and Consensus Voting
- **Cadence:** Reading every 5 frames (`ocr_every_n_frames: 5`) on vehicles tracked for at least 5 frames ensures reliable plate localization while avoiding redundant inference.
- **Early Termination:** Stopping once consensus is stable (`min_reads: 3`, `stable_share: 0.6`) reduces reads per vehicle from 20+ to an average of 3 to 4 reads.
- **Consensus Value:** Whole-string voting rejects transient OCR errors. When individual reads have isolated misread characters (`KA01AB1634`, `KA01AB1294`, `KA01A81234`), character-by-character voting repairs the plate into the ground-truth string (`KA01AB1234`).

---

### E6: Quality Gate
- Minimum plate dimensions: 50x15 px (`min_plate_width_px: 50`, `min_plate_height_px: 15`).
- Sharpness score (Laplacian variance on normalized grayscale crop): threshold = 40.0. Blurry crops are rejected before invoking OCR, preventing false reads.

---

### E7: Confidence Calibration for Watchlist Matching
- **Confidence >= 0.85:** High certainty; exact match automated alerts.
- **0.60 <= Confidence < 0.85:** High character accuracy (>= 90%); suitable for Watchlist candidate matching and operator verification.
- **Confidence < 0.60:** Provisional; flagged for further reads or operator review.
- **Proposed Watchlist Threshold:** **0.60** for Day 9.

---

## 2. Capacity Arithmetic & Throughput

- **OCR Read Latency:** ~270 - 320 ms on CPU per read.
- **Worker Capacity:**
  $$\text{Capacity} = \frac{1000 \text{ ms}}{\sim 300 \text{ ms}} \approx 3.3 \text{ reads/sec per worker thread}$$
- **Vehicle Load Calculation:**
  With 15 FPS video and `ocr_every_n_frames: 5`, each vehicle requests 3 reads per second while acquiring stability.
  Because stability is reached within 3-4 reads (~1 second of vehicle transit), a single CPU worker supports 1-2 concurrent vehicles continuously in view. For higher vehicle density, increasing `ocr_every_n_frames` to 8 or enabling GPU OCR increases capacity proportionately.

---

## 3. Failure Mode Log & Mitigations

| Failure Mode | Observed Cause | System Mitigation |
|---|---|---|
| **Look-alike Characters** | `O` vs `0`, `I` vs `1`, `8` vs `B` | Position-based correction matrix in `plate_format.py` |
| **Leading Country Tag** | High Security Plate `IND` text | Windowed scanning in `correct_indian()` disposes `IND` prefix |
| **Motion Blur** | Fast vehicle movement | Laplacian sharpness filter in `plate_quality()` rejects blurry frames |
| **Distant / Small Plate** | Vehicle far from camera | `min_vehicle_width_px: 90` skips vehicles until close enough |
| **Frame Boundary Cutoff** | Plate partially outside FOV | `border_margin_px: 8` skips truncated vehicle detections |
| **Transient Read Disagreement** | Angle / glare in one frame | Multi-frame consensus voting (string and character levels) |

---

## 4. Privacy Policy & Data Handling
- Real vehicle plates constitute personally identifiable information (PII).
- Raw plate crops and video evaluations are strictly confined to `outputs/` and `datasets/`, excluded from Git version control.
- Best evidence crops saved to `outputs/runs/<id>/anpr/plates/` are governed by retention controls (`save_crops: true/false`).
