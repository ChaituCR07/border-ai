# ADR 0035: Evaluation Methodology, Reproducibility, Run Manifests, and Statistical Rigor

## Status
Accepted

## Context
As the Border AI surveillance platform integrates multi-camera object detection and tracking pipelines into production, evaluating model performance requires scientific rigor and end-to-end reproducibility. Previous iterations relied on informal manual checks or raw validation script outputs without versioned configs, frozen evaluation subsets, or confidence intervals.

In production border monitoring, minor metric swings can translate into either critical missed intrusions (false negatives) or operator alert fatigue (false positives). To ensure credible benchmarking across edge hardware (NVIDIA Jetson, x86 servers, Apple Silicon) and CI environments, an auditable evaluation framework is required.

## Decision

1. **Run Manifest Schema & Provenance**: Every evaluation execution must produce an immutable `manifest.json` under `evaluation/runs/<run_id>/` capturing:
   - Git commit SHA and working directory dirty status.
   - Model weights SHA256 checksum and architecture identifier.
   - Dataset name, annotation path, and deterministic subset SHA256 checksum.
   - Exact runtime hyperparameters (confidence threshold, NMS IoU, image size, track buffer).
   - Execution environment metadata: platform OS, Python version, PyTorch/CUDA device, CPU cores, RAM.
   - Wall-clock runtime and random seed (fixed to `42`).

2. **Statistical Rigor & Bootstrap Confidence Intervals**:
   - Headline metrics must report non-parametric 95% bootstrap confidence intervals derived from 1,000 resamples.
   - Disallow reporting single uncalibrated point estimates for precision, recall, mAP, HOTA, and MOTA.

3. **Deterministic Frozen Subsets**:
   - High-volume public datasets are downsampled to reproducible evaluation splits stored in `evaluation/datasets/subsets/`:
     - COCO: `coco_val_1000.txt` (1,000 images sampled uniformly across classes).
     - BDD100K: `bdd_val_500_dev.txt` and `bdd_val_500_test.txt` (500-image disjoint sets stratified across weather and time-of-day).
     - MOT17: `mot17_splits.json` (explicit static vs moving sequence partitioning).

4. **Honest Metric Disclosure**:
   - In accordance with production readiness standards, aggregate numbers must be accompanied by per-class breakdowns, size bucket slices (small, medium, large), environmental slices (day vs night, clear vs rain), and error taxonomy classifications.

## Consequences
- **Positive**: Complete auditability of evaluation results; regression tests in CI run against frozen fixtures with deterministic baselines; performance claims are backed by statistical confidence intervals.
- **Negative**: Evaluation runs take slightly longer due to bootstrap resampling and manifest serialization.
