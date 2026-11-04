# Object Detection Evaluation Report

## 1. Executive Summary
This report evaluates the production object detector (`yolov8n.pt` and fine-tuned border variants) across public surveillance benchmarks (COCO val2017 subset, BDD100K dev/test) and high-resolution CCTV border fixtures.

All reported headline metrics include **95% non-parametric bootstrap confidence intervals** derived from 1,000 resamples per ADR 0035.

---

## 2. Benchmark Datasets & Subsets
- **COCO-1000**: Frozen 1,000-image subset (`evaluation/datasets/subsets/coco_val_1000.txt`) mapped via `coco_to_project.json`.
- **BDD100K-Dev (500 images)**: Weather and day/night stratified subset (`bdd_val_500_dev.txt`).
- **BDD100K-Test (500 images)**: Disjoint validation split (`bdd_val_500_test.txt`).
- **Border CCTV Mini**: Ground-truth fence-line fixture (`evaluation/fixtures/cctv_mini/annotations.json`).

---

## 3. Benchmark Mode Results (mAP Protocol: `conf = 0.001`)

| Dataset | mAP@50 (95% CI) | mAP@50:95 (95% CI) | Person AP@50 | Vehicle AP@50 | Latency (CPU) | Latency (MPS/CUDA) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **COCO-1000** | 52.8% [50.1, 55.4] | 36.4% [34.2, 38.6] | 64.2% | 58.1% | 22.4 ms | 6.8 ms |
| **BDD100K-Dev** | 48.6% [45.8, 51.3] | 31.2% [28.9, 33.5] | 49.5% | 57.8% | 23.1 ms | 7.0 ms |
| **BDD100K-Test** | 47.9% [45.2, 50.7] | 30.8% [28.5, 33.1] | 48.9% | 57.1% | 23.0 ms | 6.9 ms |
| **Border CCTV** | 86.4% [82.0, 90.5] | 68.2% [63.5, 72.8] | 89.2% | 91.5% | 24.5 ms | 7.2 ms |

---

## 4. Deployed Operating Point Performance
In operational deployments, confidence thresholds are tuned to minimize false alarms while preserving high intruder recall.

| Class | Operating Conf | Precision | Recall | F1-Score | Mean Footpoint Error |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **person** | 0.35 | 88.4% [85.2, 91.3] | 81.2% [77.6, 84.5] | 0.846 | 12.4 px |
| **car** | 0.30 | 91.2% [88.5, 93.7] | 86.5% [83.2, 89.6] | 0.888 | 15.1 px |
| **truck** | 0.35 | 87.6% [83.1, 91.5] | 82.0% [76.8, 86.7] | 0.847 | 21.3 px |
| **bus** | 0.35 | 86.0% [80.5, 90.8] | 79.4% [73.1, 85.0] | 0.826 | 24.0 px |
| **motorcycle** | 0.30 | 82.5% [76.9, 87.6] | 74.8% [68.4, 80.7] | 0.785 | 11.2 px |
| **bicycle** | 0.30 | 79.8% [73.5, 85.4] | 71.2% [64.5, 77.3] | 0.752 | 9.8 px |

---

## 5. Environmental & Slice Analysis (BDD100K & CCTV)

### By Object Size Bucket
- **Small (< 32×32 px):** AP@50 = 24.6%, Recall = 42.1%. Small targets at distance require high zoom or optical magnification.
- **Medium (32×32 to 96×96 px):** AP@50 = 54.8%, Recall = 78.5%.
- **Large (> 96×96 px):** AP@50 = 84.2%, Recall = 93.4%.

### By Time of Day
- **Daytime:** Precision = 90.1%, Recall = 85.4%, mAP@50 = 61.2%.
- **Dawn / Dusk:** Precision = 84.3%, Recall = 77.1%, mAP@50 = 53.4%.
- **Night:** Precision = 78.2%, Recall = 66.5%, mAP@50 = 42.8%. Night performance improves significantly when infrared/thermal illumination is present.

### By Weather Condition
- **Clear / Overcast:** mAP@50 = 58.7%.
- **Rainy:** mAP@50 = 47.2% (droplets on camera dome cause localized false positives).
- **Foggy / Snowy:** mAP@50 = 41.5% (contrast degradation).

---

## 6. Error Taxonomy Breakdown
Diagnostic error classification across 10,000 predictions on BDD100K:
- **Correct Detections:** 73.4%
- **Localization Errors (IoU 0.1 to 0.5):** 11.2%
- **Background False Positives:** 7.8% (foliage, fence shadows, lighting reflections)
- **Classification Confusion:** 4.1% (truck vs large bus, motorcycle vs bicycle)
- **Duplicate Detections:** 3.5% (NMS suppression threshold edge cases)
