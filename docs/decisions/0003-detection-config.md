# 0003: Detection Configuration

**Status:** Accepted  
**Date:** 2026-10-04  
**Context:** AI Engine Model Pipeline (`border-ai`)

---

## Decision

We adopt the following standard production detection configuration:
- **Model Architecture:** `yolov8n.pt`
- **Inference Resolution (`imgsz`):** 640x640
- **Device & Precision:** `device=auto` with `half=false` (safe FP32 CPU fallback; enable `half=true` FP16 on CUDA hardware)
- **Candidate Confidence Threshold (`conf`):** 0.40
- **NMS IoU Threshold (`iou`):** 0.50
- **Max Detections (`max_det`):** 300
- **Batching Strategy:** Dynamic batching across cameras via `Detector.detect_frames`

---

## Why

Comprehensive matrix benchmarking (`scripts/benchmark.py`) established that:
1. `yolov8n.pt` @ 640px achieves **~43.2 ms per frame (~23.1 FPS)** under dynamic batching, comfortably satisfying our target throughput of >= 10-15 FPS across 3 concurrent camera streams (~10.3 FPS measured live in `detect_cameras.py`).
2. Scaling to `yolov8s.pt` increases latency by ~86% to 80.3–95.2 ms/frame (10–12 FPS), failing real-time multi-camera requirements on host compute.
3. Increasing resolution to 960px doubles latency (86.4 ms for nano, 176.5 ms for small) without sufficient mAP benefit for general perimeter surveillance.
4. Dynamic batching across cameras reduces per-frame latency by ~15% by amortizing tensor transforms and Python dispatch.
5. End-to-end API latency on `POST /detect` remains well within our 150 ms ceiling (~58–72 ms).

---

## Trade-offs Accepted

- **Distant Small Targets:** Objects smaller than ~20x20 pixels in high-altitude perimeter scenes may fail candidate confidence thresholds at 640px input resolution.
- **Nighttime Low-Contrast:** Silhouette detection under poor illumination remains challenging without infrared/thermal sensors; downstream tracking (Day 5) will be utilized for temporal continuity.
- **CPU FP32 Operation:** When discrete NVIDIA GPUs are unavailable, execution runs in FP32 without hardware acceleration.

---

## Revisit If

- Per-camera FPS drops below 10 FPS once multi-object tracking (Day 5 ByteTrack) and zone tripwire evaluation (Day 6) are integrated into the processing loop.
- Dedicated edge accelerators (NVIDIA Jetson / TensorRT / CUDA) are provisioned, enabling FP16 or INT8 quantization at 960px.
