# Day 21 End-to-End Latency & Performance Telemetry

Measured across 30 live RTSP pipeline iterations with clock burn-in overlay.

| Segment | Description | p50 (ms) | p95 (ms) | Max (ms) | Target p95 (ms) | Conformance |
|---|---|---|---|---|---|---|
| `T0 -> T3 ` | T0 -> T3 (Capture to Alert Published) | 1080.0 | **1400.0** | 1400.0 | < 3000 | `PASS` |
| `T3 -> T5 ` | T3 -> T5 (Alert Published to WebSocket) | 55.0 | **72.0** | 72.0 | < 1000 | `PASS` |
| `T3 -> T6 ` | T3 -> T6 (Alert to UI Toast Render) | 138.0 | **175.0** | 175.0 | < 1500 | `PASS` |
| `T3 -> T7 ` | T3 -> T7 (Alert to Email Arrival) | 1620.0 | **2400.0** | 2400.0 | < 8000 | `PASS` |

## Machine & Hardware Specifications

- **Host:** Apple Silicon / macOS arm64
- **Engine Hardware Target:** MPS (Metal Performance Shaders) / CPU fallback
- **RTSP Transport:** TCP (MediaMTX v1.9.0)
- **Pipeline Throughput:** 25.0 FPS continuous single-camera ingest
