# ADR 0036: Detector Class Mapping, Benchmark Protocol, and Deployed Operating Points

## Status
Accepted

## Context
The border surveillance domain requires tracking 6 operational target classes: `person`, `car`, `truck`, `bus`, `motorcycle`, and `bicycle`. However, off-the-shelf and public surveillance datasets exhibit divergent taxonomies:
- COCO contains 80 classes, including irrelevant domestic categories (`couch`, `microwave`).
- BDD100K differentiates between `pedestrian` and `rider`, with distinct traffic classes.
- CCTV and thermal feeds may present small, low-contrast, or partially occluded targets.

Furthermore, academic benchmark protocols evaluate models at very low confidence thresholds (`conf = 0.001`) to integrate complete Precision-Recall curves for mAP, which is unsuitable for real-time alerting systems where high false alarm rates cause operator saturation.

## Decision

1. **Explicit Class Mapping Schemas**:
   - Class adapters must use versioned JSON mapping specifications stored in `evaluation/configs/class_maps/`.
   - In BDD100K, `pedestrian` and `rider` map to the project class `person`.
   - Unmapped classes (e.g. `traffic light`, `fire hydrant`) and crowd annotations (`iscrowd == 1`) are marked `ignore=True` during evaluation, ensuring they do not penalize model precision as false positives when overlapping valid regions.

2. **Dual-Mode Evaluation Protocol**:
   - **Benchmark Mode (`conf = 0.001`)**: Used strictly for standard mAP@50 and mAP@50:95 curve calculation.
   - **Deployed Operating Mode**: Evaluated at calibrated per-class confidence thresholds designed to balance intruder recall with operator false alarm rates:
     - `person`: 0.35
     - `car`: 0.30
     - `truck`: 0.35
     - `bus`: 0.35
     - `motorcycle`: 0.30
     - `bicycle`: 0.30

3. **Spatial Metric: Foot-Point Error**:
   - Because perimeter tripwires, fence crossings, and exclusion zones rely on physical ground contact, bounding box center errors are misleading. We evaluate Euclidean distance in pixels between the bottom-center coordinate `(x + w/2, y + h)` of the prediction and ground truth.

4. **Error Taxonomy Classification**:
   - Every unmatched or incorrect prediction is categorized into:
     - `CORRECT` (IoU >= 0.50, class matched)
     - `LOCALIZATION` (IoU between 0.10 and 0.50, class matched)
     - `CLASSIFICATION` (IoU >= 0.50, class mismatched)
     - `DUPLICATE` (IoU >= 0.50, matched to already detected ground truth)
     - `BACKGROUND` (IoU < 0.10, pure false positive)
     - `MISSED_GT` (False negative ground truth)

## Consequences
- **Positive**: Direct alignment between model evaluation metrics and perimeter rule-engine behaviors; clean mapping ensures fair comparison across COCO, BDD, and border feeds.
- **Negative**: Requires maintaining explicit class mapping files for any new external dataset integrated into testing.
