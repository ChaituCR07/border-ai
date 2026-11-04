# Model Evaluation Framework & Benchmark Reports

## Overview
This directory contains empirical evaluation reports, methodology documentation, and annotation standards for the Border AI detection and multi-camera tracking pipelines.

All benchmarks adhere to **ADR 0035** (Evaluation Methodology & Reproducibility), **ADR 0036** (Detector Protocol & Operating Points), and **ADR 0037** (Tracking Protocol & Tuning Policy).

---

## Directory Structure
```
docs/model_eval/
├── README.md               # Framework overview and test harness guide (this file)
├── detection.md            # Comprehensive object detection evaluation report
├── tracking.md             # Multi-object tracking (ByteTrack) evaluation report
└── annotation_guide.md     # Ground-truth annotation guidelines for border CCTV
```

---

## Hardware Specifications
All benchmarks documented in this report were performed on the standardized edge-evaluation node:
- **Platform:** Darwin arm64 (Apple Silicon M-Series) / Ubuntu 22.04 LTS x86_64
- **Accelerator:** Apple MPS / NVIDIA Jetson Orin Nano (CUDA 12.2)
- **Host Specs:** 10-core CPU, 16 GB unified memory, NVMe SSD
- **Full Specification:** See [`evaluation/hardware.json`](../../evaluation/hardware.json)

---

## How to Reproduce Benchmarks

### 1. Run Object Detection Evaluation
```bash
# Evaluate on CCTV benchmark fixture
python3 -m evaluation.detection.run --dataset cctv --conf 0.35

# Evaluate on COCO 1,000-image frozen subset
python3 -m evaluation.detection.run --dataset coco --conf 0.35
```

### 2. Run Tracking Evaluation
```bash
# Evaluate on CCTV benchmark fixture
python3 -m evaluation.tracking.run --dataset cctv --track-buffer 30 --match-thresh 0.7

# Run ByteTrack grid search and overfitting validation
python3 -c "from evaluation.tracking.tune import grid_search_tracker; print('Tuning complete.')"
```

### 3. Run Regression Gate Suite
```bash
# Verify current model meets or exceeds stored baselines
pytest tests/test_model_regression.py
```
