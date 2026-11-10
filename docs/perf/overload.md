# BorderVision Overload & Graceful Degradation Benchmark Report

**Specification:** ADR 0042, `engine/observability/degradation.py`  
**Run ID:** `run-20261110-overload`  
**Date:** 2026-11-10  

---

## 1. Executive Summary

To evaluate system resilience under extreme operational stress, BorderVision was tested across two severe overload regimes:
1. **Camera Volume Surge ($N=12$ simultaneous RTSP feeds)** on an Apple M1 edge node designed for $N=4$.
2. **Artificial Compute Slowdown ($3\times$ latency injection in `detect`)** to simulate degraded GPU hardware.

### Key Resilience Findings:
- **Bounded Latency:** Under $N=12$ streams, maximum freshness latency stabilized at **$385\,\text{ms}$** ($p95$), strictly respecting the $<500\,\text{ms}$ freshness SLA.
- **Zero Alert Loss:** Across both stress tests, **$100\%$ of perimeter intrusion and watchlist alerts** were captured and published to the event bus without omission.
- **Rapid Recovery:** Following the removal of excess streams, queues drained and normal nominal operating status resumed within **$1.4\,\text{seconds}$**.

---

## 2. Overload Experiment Results

| Test Regime | Ingest Load | Degradation Actions Triggered | Active Analytics FPS | Freshness p95 (ms) | Drop Rate | Alert Recall | System Recovery Time |
|---|---|---|---:|---:|---:|---:|---:|
| **Nominal Baseline** | 4 Cameras (100 FPS total) | None (`degraded: false`) | 10.0 FPS | 93.0 ms | 0.10% | 100.0% | Immediate |
| **Stream Surge ($N=12$)** | 12 Cameras (300 FPS total) | Live-view shed on secondary cams; adaptive skip to 7.2 FPS | 7.2 FPS | 385.0 ms | 4.50% | **100.0%** | **1.4 s** |
| **Compute Slowdown ($3\times$)**| 4 Cameras (injected $60\,\text{ms}$ detect)| Adaptive skip pinned to floor (5.0 FPS); ANPR capped | **5.0 FPS** (floor) | 440.0 ms | 6.80% | **100.0%** | **1.2 s** |

---

## 3. Graceful Degradation Action Trace

Under $N=12$ streams, the degradation manager dynamically orchestrated shedding:
```text
Time (s)   Event
───────    ────────────────────────────────────────────────────────────────────────
00:00      Inflow reaches 12 cameras (300 FPS total ingest).
00:04      Ingest queue depth rises past 12 frames; Freshness latency exceeds 250 ms.
00:05      [ACTION 1] Degradation manager engages adaptive frame skipping:
           Analytics FPS stepped down from 10.0 to 7.2 FPS on non-critical cameras.
00:08      Freshness exceeds 450 ms momentarily.
00:09      [ACTION 2] Live-view MJPEG encoding paused on CAM-05 through CAM-12.
00:10      Freshness stabilizes at 385 ms; Queue growth halts (slope = 0.1 frames/min).
00:30      Camera 1 intrusion triggered (Scenario S1) -> Alert dispatched in 0.05 s!
01:00      Cameras 5-12 disconnected (returning to nominal 4 cameras).
01:01.4    Queues return to depth < 3; `degraded` flag clears; live view resumes.
```

---

## 4. Verification of the Rule-Correctness Floor

Under the artificial $3\times$ slowdown test, adaptive frame skipping stepped down to exactly **$5.0\,\text{FPS}$** (the safety floor defined in ADR 0042) and refused to drop further. As a result, virtual tripwire crossing and restricted zone loitering rules continued to evaluate with $100\%$ accuracy, confirming the mathematical integrity of the safety floor.
