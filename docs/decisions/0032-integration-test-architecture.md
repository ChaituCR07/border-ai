# ADR 0032: Integration Test Architecture — Replay Modes, Scenario Specs & Assertions

## Status
Accepted

## Context
During Days 1–20, components were primarily validated in isolation or in synthetic pairs using file sources or manual demo triggers. Proving complete end-to-end functionality requires an integration testing framework that supports both fast, deterministic CI acceptance tests and realistic real-time streaming with live RTSP and network buffering.

## Decision

### 1. Three Replay Modes
We introduce three formal replay modes sharing identical scenario footage and configurations:

| Mode | Source | Clock Model | Execution Speed | Primary Use Case |
|---|---|---|---|---|
| `file_offline` | `FileSource`, back-pressure blocking | Simulated (media time + configured start) | As fast as machine allows | Deterministic scenario gating & regression testing |
| `file_paced` | `FileSource` with real-time pacing | Simulated or real wall time | 1.0x real-time | Rehearsal without external RTSP server dependencies |
| `rtsp_live` | FFmpeg -> MediaMTX -> `RTSPSource` | Real wall clock | 1.0x real-time | Operational realism, jitter & end-to-end latency validation |

### 2. Parity Rule
Any scenario passing in `file_offline` MUST pass in `rtsp_live` with relaxed time windows (events may shift by up to +/- 2.0s due to network buffering; the set of events, alerts, and classifications must be strictly identical).

### 3. Assertion Semantics
To prevent flaky tests caused by subtle ML model bounding box drift or tracker ID switches:
- Assert semantic properties: event types, camera IDs, normalized license plate keys (`plate_key`), threat priorities, threat scores, and factor breakdown.
- Never assert tracker IDs, raw bounding box pixel coordinates, or frame indices.
- Gating scenarios MUST pass 3 consecutive runs deterministically.

## Consequences
- Guarantees automated, repeatable verification across both offline gating and live RTSP streaming.
- Decouples ML variance from pipeline integration verification.
