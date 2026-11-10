# ADR 0042: Overload Behavior, Graceful Degradation Order, and Rule-Correctness Floor

## Status
Accepted

## Context
Video intelligence systems monitoring perimeter security and border checkpoints are vulnerable to load spikes (such as burst vehicle arrivals across multiple cameras or unexpected CPU contention). A naive pipeline that queues all frames under overload experiences rapid latency explosion, causing alerts to be dispatched minutes after an intruder has departed.

Conversely, blindly dropping frames risks missing fast line-crossing violations or truncating loitering dwell timers. A principled degradation policy is required that preserves event freshness and rule correctness above all else.

## Decision

1. **Guiding Principle: Freshness Over Completeness**:
   - An outdated frame is worse than a dropped frame; a real-time security alert must reflect immediate reality, not historic buffer backlogs.
   - **Under no circumstances may an alert, event journal entry, or audit log be shed.**

2. **Ordered Shedding Hierarchy**:
   When queue latency exceeds headroom thresholds ($>250\,\text{ms}$ freshness p95), work is shed in strict priority order:
   1. **Tier 1 (Live-View MJPEG Encoding)**: Live-view overlay drawing and JPEG compression are throttled or paused for unviewed cameras.
   2. **Tier 2 (Adaptive Analytics Frame Skipping)**: Non-critical cameras dynamically reduce analytics sampling rate from $10.0\,\text{FPS}$ toward the measured safety floor.
   3. **Tier 3 (ANPR Budgeting)**: OCR calls are capped globally ($10\,\text{calls/sec}$), prioritizing vehicles detected inside restricted zones or on active watchlists.
   4. **Tier 4 (Camera Priority Preservation)**: High-security checkpoint cameras (e.g. `CAM-01`) maintain full nominal rate, while secondary perimeter cameras absorb degradation first.

3. **Rule-Correctness Floor (`analytics_fps_min = 5.0 FPS`)**:
   - Frame skipping must **never** degrade below $5.0\,\text{FPS}$.
   - Empirical verification across integration scenarios S0–S2 demonstrates that below $5.0\,\text{FPS}$, fast subjects crossing narrow virtual tripwires risk being missed due to temporal sampling gaps.
   - If overload persists at $5.0\,\text{FPS}$, the system rejects non-essential ingest rather than violating rule correctness.

4. **Transparent Degradation Telemetry**:
   - Whenever degradation engages, `/metrics.json` and engine heartbeat broadcast `degraded: true` with an explicit list of active shedding actions (e.g. `"Live-view shed on CAM-04"`).
   - The operator dashboard surfaces a prominent amber status banner.
   - When queue age returns below $200\,\text{ms}$, degradation clears automatically.

## Consequences
- **Positive**: Bounded tail latency ($p95 < 500\,\text{ms}$) even under $200\%$ load surges; zero missed security alerts; zero memory leaks during overload.
- **Negative**: Live-view stream frame rate may dip briefly during major burst events on secondary cameras.
