# ADR 0041: Performance Measurement Methodology, Named Metrics, and Stability Criteria

## Status
Accepted

## Context
Performance metrics in edge video intelligence platforms are easily distorted by imprecise definitions (e.g., conflating camera stream frame rate with pipeline analytics frame rate, or reporting average latency rather than high-percentile tail latency). Furthermore, running multi-camera benchmarks on a single host without strict stability checks risks reporting transient burst speeds rather than sustainable steady-state capacity.

To establish defensible, reproducible performance claims for BorderVision, we require precise definitions, standardized timing rules, explicit workload covariates, and strict mathematical stability criteria.

## Decision

1. **Standardized Named Metrics**:
   - **Input FPS**: Frame rate ingested from the RTSP camera stream (nominally 25 FPS).
   - **Analytics FPS (per camera)**: Number of frames per second completing the full detection, tracking, rules, and ANPR pipeline within a sliding measurement window.
   - **Total Analytics FPS**: Aggregate throughput across all active cameras ($\sum_{i=1}^N \text{Analytics FPS}_i$).
   - **Processing Latency**: Wall-clock time from frame capture timestamp $t_{\text{capture}}$ to trajectory event decision $t_{\text{events}}$ (p50, p95, p99 percentiles).
   - **Annotated-Frame Latency**: Duration from capture $t_{\text{capture}}$ to the availability of the encoded MJPEG frame in the live-view streaming buffer.
   - **Freshness (Age at Inference)**: Latency from capture $t_{\text{capture}}$ to inference initiation $t_{\text{pre}}$. Monitored as the primary signal of pipeline queue buildup.
   - **Alert Latency**: End-to-end duration from event trigger frame capture to delivery at each downstream stage (Engine published $\to$ Redis $\to$ DB committed $\to$ WebSocket received $\to$ UI rendered $\to$ Email worker dispatched).
   - **Drop Rate**: Ratio of discarded frames to total frames delivered ($\text{dropped} / \text{received}$).
   - **Per-Stage Latency**: Explicit breakdown of individual pipeline stages: `decode`, `preprocess`, `detect` (device-synchronized), `postprocess`, `track`, `rules`, `anpr_locate`, `anpr_ocr`, `consensus`, `serialise_publish`, `render`.
   - **Sustained Capacity ($N^*$)**: Maximum simultaneous camera count maintaining steady-state criteria.

2. **Timing Protocol & Hardware Synchronization**:
   - High-resolution monotonic timers (`time.perf_counter_ns`) are used exclusively for all in-process timings.
   - When measuring GPU/MPS device execution time, synchronization barriers (`torch.cuda.synchronize()` or `torch.mps.synchronize()`) must be invoked before stopping the timer when `PERF_SYNC=1`. Both synchronized (pure compute) and unsynchronized wall-clock latencies are reported.
   - All benchmark runs follow a three-phase window:
     - **Warm-up**: 60 seconds (discarded; allows JIT compilation, buffer allocation, and cuDNN/Metal autotuning to settle).
     - **Measurement Window**: 300 seconds (report mode) or 90 seconds (fast iteration mode).
     - **Cool-down**: 30 seconds (discarded).
   - All percentile metrics are computed from high-dynamic-range histograms (`HdrHistogram`) with microsecond resolution and merged across cameras.

3. **Workload Profiles & Covariates**:
   - Workload density dramatically influences tracking and ANPR compute. Benchmark tests must be classified into standard profiles:
     - `light`: Sparse scene, $<2$ detections/frame, zero plates.
     - `typical`: Standard border gate traffic, $3-6$ detections/frame, 1-2 license plates visible.
     - `heavy`: Crowded chokepoint, $>8$ detections/frame, continuous vehicle flow with multiple plates.
   - Mean detections/frame and OCR calls/second must be reported as covariates for every test.
   - Multi-camera tests must use distinct clip feeds with staggered start offsets ($\ge 7\,\text{s}$) to avoid artificial synchronous compute spikes.

4. **Rigorous Run Stability Criterion**:
   - A benchmark run is designated as **VALID** only if all of the following conditions hold across the measurement window:
     1. Queue Depth Trend: Linear regression slope of each internal queue $\le 1.0\,\text{frame/minute}$.
     2. Queue Boundedness: Final queue depth $< 50\%$ of maximum buffer capacity.
     3. Drop Rate: Sustained live frame drop rate $< 1.0\%$.
     4. Freshness: $p95$ freshness latency $< 500\,\text{ms}$.
     5. Thermal & Clock Stability: CPU/GPU clocks within $10\%$ of start values (no thermal throttling).
     6. Process Health: Zero unexpected process restarts or memory leaks.
   - Any run failing these criteria is classified as **UNSTABLE** or **THROTTLED** and excluded from capacity medians.

5. **Capacity Statements & Extrapolations**:
   - Only measured values on physical hardware carry direct performance claims. Extrapolations to other hardware configurations must follow ADR 0043 guidelines.

## Consequences
- **Positive**: Eliminates misleading average numbers; exposes real tail latency and queue saturation; ensures all runs across different days and branches are directly comparable.
- **Negative**: Increases benchmark execution duration due to mandatory warm-up periods and multi-repetition runs.
