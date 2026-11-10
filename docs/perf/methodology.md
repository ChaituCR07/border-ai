# BorderVision Performance Testing Methodology & Environment

**Document Version:** 1.0.0  
**Associated Architecture Decision Record:** ADR 0041  
**Status:** Frozen prior to benchmark execution  
**Target Hardware Platform:** Apple M1 (8 cores: 4 performance + 4 efficiency), 8 GB Unified Memory, macOS 26.6.2  

---

## 1. Pre-Agreed Target SLAs (Frozen)

All benchmark measurements are evaluated against the following pre-established operational SLA targets:

| Metric | Target SLA | Stretched Target | Operational Rationale |
|---|---|---|---|
| **Analytics FPS / camera** | $\ge 10.0\,\text{FPS}$ | $\ge 15.0\,\text{FPS}$ | Maintains tracker track continuity and line crossing accuracy |
| **Processing Latency ($p95$)** | $< 250\,\text{ms}$ ($N=1$) | $< 400\,\text{ms}$ ($N=4$) | Real-time situational awareness threshold for operator display |
| **Freshness ($p95$)** | $< 500\,\text{ms}$ | $< 300\,\text{ms}$ | Prevents stale frame queueing during burst arrivals |
| **Alert Latency ($p95$, capture $\to$ WS)** | $< 1.5\,\text{s}$ | $< 1.0\,\text{s}$ | Immediate gate interlock and perimeter deterrence trigger |
| **Alert Latency ($p95$, capture $\to$ Email)**| $< 8.0\,\text{s}$ | $< 5.0\,\text{s}$ | External dispatch notification bound |
| **Sustained Live Drop Rate** | $< 1.0\%$ | $< 0.1\%$ | Bounded frame dropping policy under nominal stream load |
| **API Latency ($p95$, 50 concurrent users)**| $< 200\,\text{ms}$ | $< 100\,\text{ms}$ | High-concurrency command dashboard responsiveness |
| **Database Sink Ingest Capacity** | $\ge 3\times$ peak event rate | $\ge 10\times$ peak | Handles burst surges without consumer group lag |
| **Memory Growth (Post Warm-Up)** | $< 10\% / \text{hour}$ | $0\%$ leak | Prevents long-term OOM crashes in 24/7 border operations |

---

## 2. Standard Metric Definitions

Every reported performance table strictly adheres to the following definitions (ADR 0041):

1. **Input FPS**: Stream rate emitted by the camera/simulator (nominal 25 FPS, H.264).
2. **Analytics FPS (per camera)**: Actual frames completing full inference, tracking, rule evaluation, and ANPR per second within the steady-state window.
3. **Total Analytics FPS**: Aggregate system throughput across all camera streams ($\sum \text{Analytics FPS}_i$).
4. **Processing Latency**: Duration from frame capture timestamp $t_{\text{capture}}$ to rule and event emission $t_{\text{events}}$.
5. **Annotated Frame Latency**: Duration from capture $t_{\text{capture}}$ to the availability of the encoded MJPEG frame in the live-view streaming buffer.
6. **Freshness (Age at Inference)**: Latency from $t_{\text{capture}}$ to inference commencement $t_{\text{pre}}$. Monitored to detect queue buildup.
7. **Drop Rate**: Ratio of discarded frames to total frames delivered ($\text{dropped} / \text{received}$).
8. **Per-Stage Latency**: Explicit breakdown of individual pipeline stages:
   - `decode`: RTSP frame demux and H.264 decoding.
   - `preprocess`: Letterbox resizing and RGB normalization.
   - `detect`: YOLO inference forward pass (device-synchronized when `PERF_SYNC=1`).
   - `postprocess`: Non-Maximum Suppression (NMS) and coordinate mapping.
   - `track`: ByteTrack state estimation and Kalman prediction.
   - `rules`: Zone containment, loitering calculation, and line-crossing intersection tests.
   - `anpr_locate`: Vehicle crop filtering and license plate localization.
   - `anpr_ocr`: Optical character recognition execution.
   - `consensus`: Multi-frame positional character voting.
   - `serialise_publish`: Event envelope formatting and Redis stream dispatch.
   - `render`: MJPEG bounding box overlay rendering and JPEG encoding.

---

## 3. Workload Profiles & Covariates

Because computer vision pipelines perform variable amounts of tracking and OCR depending on scene activity, all tests specify their workload profile:

| Profile | Scene Description | Expected Detections / Frame | Expected OCR Calls / sec |
|---|---|---|---|
| **`light`** | Sparse desert perimeter, open roadway, rare motion | $< 2.0$ | $< 0.2$ |
| **`typical`** | Mixed border gate traffic: pedestrians, moving cars | $3.0 - 6.0$ | $0.8 - 2.0$ |
| **`heavy`** | Crowded checkpoint chokepoint, dense vehicle queues | $> 8.0$ | $> 4.0$ |

All multi-camera configurations ($N \in \{2, 4, 8\}$) use different video clips with staggered start offsets ($\ge 7\,\text{seconds}$) to prevent synchronous batch alignment artifacts.

---

## 4. Run Stability Criteria

A measurement run is considered **VALID** if and only if it satisfies all of the following criteria across the steady-state window:

1. **Queue Stability**: Linear regression slope of each internal queue $\le 1.0\,\text{frames/minute}$.
2. **Buffer Headroom**: Final queue depth $< 50\%$ of maximum buffer capacity.
3. **Drop Boundary**: Sustained drop rate $< 1.0\%$.
4. **Freshness Bound**: $p95$ freshness latency $< 500\,\text{ms}$.
5. **No Thermal Throttling**: Clock frequencies remain within $10\%$ of initial state.
6. **Zero Restarts**: No unhandled exceptions or worker restarts.

---

## 5. Execution Environment Checklist

- **Host Machine:** Apple M1 (8 cores: 4 performance + 4 efficiency)
- **Host Memory:** 8 GB Unified Memory (LPDDR4X)
- **Host OS:** macOS 26.6.2 (Darwin 25G83)
- **Runtime Environment:** Python 3.13.1, PyTorch with MPS (Metal Performance Shaders) backend
- **Power Configuration:** AC connected, Low Power Mode disabled, system sleep prevented during execution
- **Database & Cache Infrastructure:** PostgreSQL 16, Redis 7 (persistent event stream)
- **Stream Simulator:** FFmpeg hardware-accelerated H.264 loopback (`-c copy`)
