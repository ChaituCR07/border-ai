# Dataset Licenses & Data Governance

This document records the licenses, terms of use, and redistribution policies for evaluation and benchmark datasets used in the Border-AI platform.

---

## 1. Public Benchmark Datasets

| Dataset | Split Used | License / Terms | Commercial Terms | Redistribution Policy |
|---|---|---|---|---|
| **COCO (Common Objects in Context)** | `val2017` subset (1,000 images) | **CC BY 4.0** | Allowed with attribution | Never commit images or full annotations to Git; commit only deterministic image ID lists. |
| **BDD100K (Berkeley DeepDrive)** | `val` subset (1,000 frames) | BDD100K License / Academic & Evaluation | Non-commercial evaluation | No redistribution of raw images; store under external `EVAL_DATA_ROOT`. |
| **MOT17 (Multiple Object Tracking Benchmark)** | `train` sequences (7 sequences) | MOT Challenge Terms | Non-commercial research & benchmarking | Never commit raw sequences; process via external path or synthetic fixtures. |
| **UA-DETRAC** | Test subsets | Research License | Benchmark evaluation | Retain external dataset directory. |

---

## 2. Proprietary & Controlled Project CCTV Footage

| Dataset Component | Source | Rights & Authorization | Usage Scope |
|---|---|---|---|
| **BorderVision Scenario Clips (S0–S3)** | Controlled staging & synthetic rendering | Owned by Border-AI project team | Pipeline verification, regression testing, and showcase demonstration. |
| **CCTV Mini-Set (30 frames)** | Self-recorded / permitted controlled staging | Full intellectual property rights | Committed under `evaluation/fixtures/cctv_mini/` strictly for automated regression testing. |
| **Overlaid Plates** | Synthetic compositing on authorized scenes | Project owned | Exclusively used for pipeline integration testing; explicitly excluded from ANPR model accuracy claims. |
