# Border-AI Release Facts & Verification Metrics (v1.0.0)

This document serves as the **Single Source of Truth** for all quantitative claims, performance benchmarks, test metrics, and architectural specifications across the Border-AI documentation suite.

---

## 1. Headline Platform Benchmarks (Audited)

| Component / Subsystem | Benchmark Metric | Measured Value (95% CI) | Test Set / Dataset | Run Identifier | Reference Report |
|---|---|---|---|---|---|
| **Object Detection (YOLOv8)** | Deployed mAP@50 | **86.4%** [82.0, 90.5] | Border CCTV Mini (n=500) | `run-20261108-cctv-det` | [`docs/model_eval/detection.md`](../model_eval/detection.md) |
| **Object Detection (YOLOv8)** | Benchmark mAP@50:95 | **36.4%** [34.2, 38.6] | COCO-1000 Validation | `run-20261108-coco-bench` | [`docs/model_eval/detection.md`](../model_eval/detection.md) |
| **Multi-Object Tracking** | Overall HOTA | **64.6%** [62.8, 66.3] | MOT17 Static CCTV Splits | `run-20261108-mot17-track` | [`docs/model_eval/tracking.md`](../model_eval/tracking.md) |
| **Multi-Object Tracking** | Overall MOTA | **71.4%** [69.2, 73.5] | MOT17 Static CCTV Splits | `run-20261108-mot17-track` | [`docs/model_eval/tracking.md`](../model_eval/tracking.md) |
| **Multi-Object Tracking** | Track Continuity | **92.2%** | MOT17 Static CCTV Splits | `run-20261108-mot17-track` | [`docs/model_eval/tracking.md`](../model_eval/tracking.md) |
| **ANPR Recognition** | Consensus Plate Accuracy | **98.4%** [97.1, 99.3] | CCTV Multi-Angle Synthetic/Real | `run-20261109-anpr-eval` | [`docs/model_eval/anpr.md`](../model_eval/anpr.md) |
| **ANPR Recognition** | Character Error Rate (CER) | **1.2%** | Standard HSRP Plates (n=1,000) | `run-20261109-anpr-eval` | [`docs/model_eval/anpr.md`](../model_eval/anpr.md) |
| **False-Positive Robustness** | FP Alerts ($\ge\text{HIGH}$) | **0 FP alerts** in 4.25 camera-hours | Border Uneventful Footage | `run:exp-20261112-01` | [`docs/testing/false_positive_report.md`](../testing/false_positive_report.md) |
| **Watchlist False Matches** | False Match Rate | **0.0 / 1,000 reads** | 100-Plate Watchlist Matrix | `run:wl-20261112-01` | [`docs/testing/false_positive_report.md`](../testing/false_positive_report.md) |
| **Pipeline Latency** | Detection Latency (p50) | **8.0 ms** / frame | Apple Silicon M1 MPS (YOLOv8s) | `run-20261110-primary-scaling` | [`docs/perf/performance_report.md`](../perf/performance_report.md) |
| **Alert Latency** | Trigger $\to$ WebSocket (p95)| **0.05 s** (50 ms) | Composed Stack (N=4 cameras) | `run-20261110-primary-scaling` | [`docs/perf/performance_report.md`](../perf/performance_report.md) |
| **Sustained Scale ($N^*$)** | Camera Capacity SLA | **8 cameras** sustained | <250ms latency, <1% drop target | `run-20261110-primary-scaling` | [`docs/perf/capacity.md`](../perf/capacity.md) |
| **Storage Optimization** | Track Aggregation | **99.5% reduction** | vs. raw per-frame telemetry | `run-20261110-capacity` | [`docs/perf/capacity.md`](../perf/capacity.md) |

---

## 2. Engineering Verification Statistics

| Metric Category | Count / Value | Verification Source |
|---|---|---|
| **Total Git Commits** | > 450 commits | Git log (`git rev-list --count HEAD`) |
| **Total Test Cases** | > 280 automated tests | Pytest, Vitest, Playwright, Compose test runners |
| **Database Migrations** | 8 idempotent migrations (`001` to `008`) | PostgreSQL schema registry |
| **REST API Endpoints** | 38 documented operations | OpenAPI 3.0 specification (`docs/api/openapi.json`) |
| **WebSocket Message Types** | 6 bi-directional event schemas | `backend/src/websocket/protocol.ts` |
| **Architecture Decision Records** | 55 accepted ADRs (`0001` through `0055`) | `docs/decisions/` |
| **Docker Compose Services** | 10 orchestrated containers | `docker-compose.yml` |
| **Internal Docker Networks** | 3 segregated bridge planes (`frontend`, `data`, `media`) | `docker-compose.yml` (ADR 0050) |
| **Published Host Ports** | 2 ports only (`80`, `443` on Nginx) | Nginx edge reverse proxy |
| **ASVS 4.0 Security Checks** | 30 / 30 automated controls passed | `backend/tests/security/` (ADR 0048) |
| **Resilience Scenarios** | 12 / 12 fault-injection scenarios passed (R1–R12) | `docs/deployment/resilience_results.md` |

---

## 3. Reference Test Hardware Environments

### Primary Performance Environment (Apple Silicon M1)
- **Model:** Apple MacBook Pro (13-inch, 2020)
- **CPU:** Apple M1 (8 cores: 4 performance + 4 efficiency)
- **GPU:** Apple M1 (8-core integrated GPU, Metal / MPS acceleration)
- **Memory:** 8 GB Unified Memory
- **Operating System:** macOS Darwin 24.6.2

### Server / GPU Production Target (x86_64 CUDA)
- **Host CPU:** AMD Ryzen 9 5900X (12 cores, 24 threads) or Intel Xeon Gold 6248
- **Host GPU:** NVIDIA GeForce RTX 3080 (10 GB VRAM) / NVIDIA Tesla T4 (16 GB)
- **Driver / Runtime:** NVIDIA Driver 535.129.03, CUDA 12.1, NVIDIA Container Toolkit
- **Operating System:** Ubuntu 22.04 LTS (Kernel 5.15)
