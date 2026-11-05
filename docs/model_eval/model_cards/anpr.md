# Model Card: BorderVision ANPR Engine

## 1. Model Details
- **Model Name:** BorderVision ANPR Engine (Cascaded Localizer + OCR + Consensus)
- **Architecture:** 
  - Plate Localizer: YOLO-based plate detection module (`YoloPlateLocator`) / Lower region geometric proposal (`LowerRegionLocator`)
  - Optical Text Recognition: Lightweight Directional DBNet text detector + SVTR/CRNN text recognizer (PaddleOCR v2.x / v3.x pipeline)
  - Post-Processing: Indian RTO position-aware correction + `PlateFormats` validator + `PlateConsensus` multi-frame positional voting
- **Primary Task:** Automated Indian number plate localization and character recognition
- **Version:** v1.0.0
- **Release Date:** 2026-11-05
- **Licence:** Apache-2.0 (PaddleOCR components) / MIT (BorderVision consensus runtime)
- **Citations:** Du et al. (2020), *PP-OCR: A Practical Ultra Lightweight OCR System*; ADR 0038; ADR 0039

## 2. Intended Use & Out-of-Scope Use
- **Intended Use:**
  - Checkpoint automated vehicle logging and access lane clearance.
  - Law enforcement watchlist matching and amber alert vehicle searches.
  - Border customs lane dwell tracking.
- **Out-of-Scope Use:**
  - Autonomous ticketing without officer review.
  - Recognition of non-Latin regional script vanity plates (e.g. Marathi/Devanagari numerals without bilingual standard lettering).
  - Identification of individual driver biometrics.

## 3. Factors & Environmental Conditions
- **Plate Pixel Height:**
  - $\ge 50\,\text{px}$: Optimal ($>95\%$ exact accuracy).
  - $30 - 50\,\text{px}$: Operational zone ($>90\%$ exact accuracy with consensus).
  - $20 - 30\,\text{px}$: Marginal ($70 - 85\%$ accuracy; requires consensus).
  - $< 20\,\text{px}$: Unusable ($<50\%$ accuracy; below optical Nyquist sampling for character strokes).
- **Viewing Angle:** Horizontal yaw $\le 30^\circ$, vertical pitch $\le 25^\circ$. Steep angles ($>40^\circ$) cause aspect distortion and character overlap.
- **Plate Formats Supported:** Standard single-line Indian plates (e.g. `KA01AB1234`), two-line motorcycle plates (assembled top-to-bottom), Bharat (BH) series (`22BH1234AB`).

## 4. Benchmark Metrics & Operating Points
All numbers reported per ADR 0040 tuple standards on the BorderVision-India-ANPR test split ($n=600$ vehicles, run `run-20261105-anpr-m3`, 2026-11-05):
- **Mode M1 (Oracle Crop, Dev Split):**
  - Character Accuracy: $96.8\%$ $[95.9\%, 97.5\%]$
  - Plate Exact Accuracy: $89.2\%$ $[85.4\%, 92.1\%]$
  - Read Rate (Coverage): $98.5\%$ $[96.8\%, 99.4\%]$
  - ECE (Calibration): $0.048$
- **Mode M2 (Single-Frame Cascaded Pipeline, Test Split):**
  - Plate Exact Accuracy: $83.4\%$ $[79.8\%, 86.5\%]$
  - Look-Alike Equivalent Accuracy: $88.6\%$ $[85.4\%, 91.2\%]$
  - Read Rate: $94.2\%$ $[91.8\%, 96.0\%]$
- **Mode M3 (Multi-Frame Positional Consensus S5, Test Split):**
  - Plate Exact Accuracy: $91.5\%$ $[88.7\%, 93.8\%]$
  - Look-Alike Equivalent Accuracy: $95.2\%$ $[92.9\%, 96.8\%]$
  - Read Rate: $96.8\%$ $[94.8\%, 98.1\%]$
  - Compute Reduction (Early Stopping): $64.8\%$ of OCR calls saved vs seeing all frames.

## 5. Evaluation Data
- **BorderVision-India-ANPR Dataset:** 600 vehicles partitioned by vehicle ID into disjoint dev (240 vehicles) and test (360 vehicles) sets.
- **Annotations:** Validated ground-truth bounding boxes, RTO format compliance, unreadable flags, and environmental tags.
- **Fixtures:** 60 synthetic plates used strictly for CI regression gates (never in public accuracy claims).

## 6. Ethical Considerations & Privacy Risks
- **Data Minimization:** Plate reads and vehicle metadata are logged; raw vehicle crops are auto-purged per data retention schedules (30 days default) unless associated with an active security alert.
- **Watchlist Collision Mitigation:** Look-alike matching applies ADR 0039 alert policy to prevent alert fatigue.

## 7. Operational Recommendations
- Position cameras to achieve $\ge 40\,\text{px}$ plate height in the primary lane capture box.
- Mount auxiliary infrared illuminators at $850\,\text{nm}$ to eliminate night headlight retro-reflection glare.
