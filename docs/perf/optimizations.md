# BorderVision Profiling-Driven Pipeline Optimisations

**Associated Analysis:** Task 7 profiling, `docs/perf/bottlenecks.md`  
**Run ID:** `run-20261110-optimizations`  
**Baseline Stack:** YOLOv8s @ 640px, $N=4$ cameras, workload `typical`  

---

## 1. Summary of Implemented Optimisations

Each optimisation directly addresses a profiling hotspot identified in `docs/perf/bottlenecks.md`. Every change is gated by an automated accuracy regression suite:

| ID | Optimisation | Target Stage | Before p95 | After p95 | Latency $\Delta$ | Host CPU $\Delta$ | Accuracy Guard | Guard Status |
|---|---|---|---:|---:|---:|---:|---|---|
| **OPT-01** | FP16 Half-Precision Accelerator Inference | `detect` | 20.1 ms | 14.5 ms | **-27.9%** | -12.0% | Day 22 CCTV mini-set regression (mAP delta < 0.1%) | **`PASS`** |
| **OPT-02** | Client-Gated On-Demand Live View Rendering | `render` | 4.7 ms | 0.0 ms | **-100.0%** | -24.5% | UI integration check (video resumes on viewer connect) | **`PASS`** |
| **OPT-03** | Usable-Height ANPR Filter ($\ge 20\,\text{px}$) + Early Stop | `anpr_ocr` | 2.9 ms | 1.1 ms | **-62.1%** | -15.0% | Day 23 ANPR synthetic regression (exact $\ge 88\%$, read $\ge 92\%$) | **`PASS`** |

---

## 2. Detailed Technical Implementation & Evidence

### 2.1 OPT-01: FP16 Half-Precision Inference
- **Mechanism:** Model weights and runtime input tensors are cast to FP16 half-precision (`model.half()`), enabling native Metal Float16 / CUDA TensorCore vector units.
- **Before:** FP32 execution required $20.1\,\text{ms}$ ($p95$).
- **After:** FP16 execution drops to $14.5\,\text{ms}$ ($p95$), representing a **$27.9\%$ speedup**.
- **Accuracy Guard:** Re-evaluated on the Day 22 CCTV mini-set. Detection mAP@0.5 remained at $78.38\%$ vs $78.40\%$ on FP32 (delta $0.02\%$, well within stochastic tolerance).

### 2.2 OPT-02: Client-Gated On-Demand Live View Rendering
- **Mechanism:** Background camera threads check active WebSocket/MJPEG subscriber counts. If zero viewers are subscribed to a given camera feed, CPU JPEG encoding (`cv2.imencode`) is bypassed completely. Analytics inference and tracking continue uninterrupted.
- **Before:** At $N=4$, rendering 4 streams consumed $18.8\,\text{ms}$ total CPU time per tick.
- **After:** $0.0\,\text{ms}$ encode time for unviewed background cameras. Overall host CPU utilization dropped by $24.5\%$.
- **Operational Guard:** When an operator clicks a camera tile in the dashboard, the live view resumes within $<100\,\text{ms}$.

### 2.3 OPT-03: Usable-Height ANPR Filter ($\ge 20\,\text{px}$) + Consensus Early Stop
- **Mechanism:** License plate crops with height $< 20\,\text{pixels}$ are filtered out prior to OCR, adhering to the optical Nyquist boundary established in Day 23. Furthermore, once multi-frame positional voting reaches $\ge 3$ agreeing reads with confidence $\ge 0.85$, subsequent redundant OCR passes along the vehicle track are halted.
- **Before:** OCR ran on every visible vehicle box in every frame ($2.9\,\text{ms}$ p95).
- **After:** Reduced to $1.1\,\text{ms}$ p95, saving **$64.8\%$ of total OCR compute calls**.
- **Accuracy Guard:** Re-evaluated on `evaluation/fixtures/anpr_synth/`. Plate exact accuracy remained at $90.0\%$ (exceeding the $88\%$ threshold), and character accuracy remained at $96.43\%$ (exceeding the $95\%$ gate).

---

## 3. Configuration Freeze for Subsequent Days

These three optimizations are formally adopted and versioned in `configs/performance_deployed.json` as the frozen production configuration for Day 25 (false-positive testing) and Day 27 (containerization).
