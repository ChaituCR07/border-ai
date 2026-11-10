# BorderVision Pipeline Bottleneck Profiling & Stage Accounting

**Profiling Context:** Steady-state profile of primary configuration ($N=4$ cameras, YOLOv8s @ 640px, workload `typical`)  
**Associated Analysis:** Task 6 profiling, ADR 0041, `docs/perf/performance_report.md`  
**Run ID:** `run-20261110-bottlenecks`  

---

## 1. Stage Latency Ranking & Fraction of Frame Time

Profiling traces across 12,000 processed frames yield the following rank-ordered latency distribution:

| Rank | Pipeline Stage | p50 (ms) | p95 (ms) | Fraction of Frame Latency | Root-Cause Mechanism | Candidate Optimisation |
|---|---|---:|---:|---:|---|---|
| **1** | **`detect`** | `8.0` | `20.1` | **51.8%** | Tensor forward-pass execution on neural accelerator (YOLOv8s backbone + head) | FP16 half-precision, multi-camera adaptive batching |
| **2** | **`render`** | `1.9` | `4.7` | **11.4%** | Software JPEG encoding (`cv2.imencode`) and BGR overlay drawing for MJPEG | On-demand rendering (only encode when client connected), reduced JPEG quality (75%) |
| **3** | **`decode`** | `1.3` | `3.1` | **8.2%** | RTSP H.264 NAL parsing and CPU frame decompression | Hardware VideoToolbox / NVDEC, `-c copy` pass-through |
| **4** | **`anpr_ocr`** | `1.2` | `2.9` | **7.4%** | Secondary crop text recognition (Directional DBNet + SVTR text recognizer) | Usable-height skip ($<20\,\text{px}$), consensus early-stop ($64.8\%$ calls saved) |
| **5** | **`track`** | `1.3` | `3.1` | **7.1%** | ByteTrack Kalman filter state covariance projection and Hungarian assignment | Vectorized NumPy IoU matrix computation |
| **6** | **`preprocess`** | `0.8` | `1.7` | **4.2%** | Bilinear letterbox aspect resize and UINT8 $\to$ FP32 tensor normalization | Pinned host memory buffers, pre-allocated tensor cache |
| **7** | **`postprocess`**| `0.9` | `2.0` | **4.0%** | Non-Maximum Suppression (NMS) score thresholding and coordinate scaling | Pre-filtering candidate boxes at score $\le 0.15$ prior to NMS |
| **8** | **`rules`** | `0.6` | `1.3` | **2.9%** | Polygon ray-casting containment and line-crossing segment intersection | Pre-check zone bounding box overlap before ray-casting |
| **9** | **`serialise_pub`**| `0.4` | `0.9` | **1.8%** | JSON envelope serialization and Redis stream dispatch (`XADD`) | Pipelined batch dispatch, `orjson` binary serialization |
| **10**| **`consensus`** | `0.3` | `0.6` | **1.2%** | Multi-frame positional character alignment and agreement checking | In-memory track read ring buffer |

---

## 2. Deep-Dive Flamegraph & CPU Architecture Accounting

Profiling using CPU sampling and Metal/CUDA trace logs reveals three distinct operational regimes:

### 2.1 The Accelerator Boundary (`detect`)
- **Forward-Pass Dominance:** The YOLOv8s convolution and attention layers consume $51.8\%$ of total processing latency.
- **Host-Device Transfer Overhead:** Copying $640\times 640\times 3$ FP32 tensors across host and device introduces a $0.8\,\text{ms}$ latency penalty per frame. Moving to contiguous, pinned memory tensors minimizes transfer stalls.
- **Precision Opportunity:** Switching from FP32 to FP16 half-precision reduces forward pass latency by $\approx 22\%$ with zero degradation in detection recall ($<0.1\%$ mAP variance).

### 2.2 The Live-View Overhead Trap (`render`)
- **Software JPEG Encoding:** Every camera stream previously encoded an MJPEG frame on every cycle, regardless of whether any human operator was viewing the stream in the web UI.
- **CPU Penalty:** JPEG compression is purely CPU-bound. At $N=8$ cameras, rendering consumed over $120\%$ host CPU core equivalent just generating unseen frames.
- **Optimisation Impact:** Gating MJPEG encoding to execute **only when an active HTTP/WebSocket viewer is subscribed** completely eliminates this overhead in headless scenarios, unlocking headroom for 4 additional camera streams.

### 2.3 Secondary ANPR Chokepoint (`anpr_ocr`)
- Optical character recognition requires secondary crop extraction and forward pass through PaddleOCR.
- In dense vehicle scenes, unregulated OCR triggers on distant, blurry plates ($<20\,\text{px}$ height) where accuracy is $<50\%$ (Day 23 slice analysis).
- Enforcing the **Usable-Height Filter** ($\ge 20\,\text{px}$) eliminates $28\%$ of useless OCR invocations, and temporal **Early-Stopping** saves an additional $64.8\%$ of calls.

---

## 3. Prioritized Optimization Action Plan

Based on measured latency shares, optimizations are prioritized by return on investment:

1. **Optimisation 1 (Inference):** FP16 half-precision execution for detector and OCR.
2. **Optimisation 2 (Live-View):** Client-gated on-demand MJPEG rendering with adaptive JPEG quality.
3. **Optimisation 3 (ANPR):** Resolution-gated OCR invocation with multi-frame early stopping.
4. **Optimisation 4 (Database Sink):** Pipelined multi-row inserts and index maintenance.
