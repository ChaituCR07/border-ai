# ADR 0038: ANPR Evaluation Protocol, Stage Funnel, and Split Policy

## Status
Accepted

## Context
Automatic Number Plate Recognition (ANPR) is critical for border checkpoint security, stolen vehicle detection, and watchlist enforcement. Unlike generic text recognition on documents, operational ANPR operates across a cascaded visual pipeline: vehicle detection, license plate localization, optical character recognition, format validation, and multi-frame temporal consensus.

Evaluating ANPR solely by character error rate (CER) on cropped plates obscures pipeline failures (such as missed detections, clipped plate borders, or formatting rejections). Furthermore, evaluating on random frame splits introduces massive data leakage, as frames from the same vehicle pass-by clip share identical lighting, camera geometry, and plate text.

## Decision

1. **Three-Tier Evaluation Modes**:
   - **Mode M1 (Oracle Crops)**: Evaluates the OCR engine, preprocessor, and validator on ground-truth plate bounding boxes with a +5% margin. Isolates character recognition accuracy and format validation from localization errors.
   - **Mode M2 (Single-Frame Pipeline)**: Evaluates the cascaded pipeline (vehicle detection $\to$ plate localizer $\to$ OCR $\to$ validator) on individual frames. Measures localization precision/recall and the performance degradation ($\Delta \text{M1} \to \text{M2}$).
   - **Mode M3 (Track-Level Multi-Frame Consensus)**: Evaluates consensus aggregation across complete vehicle trajectory tracks. Benchmarks voting strategies (S1 best-confidence, S2 first-valid, S3 majority, S4 confidence-weighted, S5 positional voting) and early-stopping compute efficiency.

2. **Vehicle/Session-Level Split Policy**:
   - Dataset splits are strictly partitioned by **Vehicle / Session ID**, never by frame.
   - All frames of a given physical vehicle reside entirely within either `dev` (~40%) or `test` (~60%).
   - The test set is larger because it carries public performance claims.
   - CI automated tests verify vehicle ID disjointness between splits.

3. **Stage-by-Stage Monotone Attribution Funnel**:
   - Performance must be tracked across a monotonic attribution funnel derived from the exact same vehicle set:
     $$\text{Vehicles} \to \text{Detected (IoU} \ge 0.5) \to \text{Localized (IoU} \ge 0.5) \to \text{OCR text} \to \text{Exact match} \to \text{Validated} \to \text{Consensus exact}$$
   - Every stage transition reports both conditional step retention and cumulative retention with 95% Wilson score confidence intervals.

4. **Ground Truth and Unreadable Handling**:
   - Severely damaged, obscured, or non-visible plates are annotated with `unreadable = true`.
   - Unreadable plates are excluded from character/exact accuracy denominators to avoid penalizing OCR for impossible inputs, but are strictly counted in **Coverage / Read-Rate** denominators.
   - All published reports must state the exact count of excluded unreadable plates.

5. **Operational Slice Analysis**:
   - ANPR performance must be stratified across:
     - **Plate Height**: `<20px`, `20-30px`, `30-50px`, `50-80px`, `>80px`. Reports derive the minimum plate height required for $\ge 90\%$ accuracy (the camera placement rule).
     - **Viewing Angle**: frontal, oblique, steep.
     - **Lighting Condition**: day, night, rain, glare, blur.
     - **Vehicle Type**: car, motorcycle (two-line layout), bus, truck.

## Consequences
- **Positive**: Eliminates split data leakage; attributes errors directly to the failing pipeline stage; provides concrete camera zoom and mounting specifications for field deployment.
- **Negative**: Requires rigorous vehicle-level track tracking and metadata annotation in dataset adapters.
