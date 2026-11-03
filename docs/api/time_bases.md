# Time Bases & Clock Semantics

This document defines the five distinct time bases used across the Border-AI system, their canonical sources, update semantics, and integration rules.

---

## 1. The Five Clocks

| Clock | Where it appears | Intended meaning | Source / Format |
|---|---|---|---|
| **Media time** | Frame presentation timestamp (PTS), `FileSource` frame offsets | Position within the recorded video stream | Offset in seconds (`float`) from media start (e.g., `0.040s`) |
| **Event time** | `events.timestamp`, journal envelopes, Redis stream payloads | When the physical event happened in reality | ISO 8601 UTC with microsecond precision (`YYYY-MM-DDTHH:MM:SS.ffffffZ`). In `rtsp_live`, real wall time. In `file_offline`, simulated time (`scenario_start + media_time`). |
| **Engine wall time** | `engine_alert_at`, heartbeats (`engine:status`) | When the AI engine inference completed | Current engine system clock in UTC microsecond ISO format. |
| **DB insertion time** | `alerts.received_at`, `notifications.created_at` (`now()`) | When the persistent layer ingested and recorded the record | Database server `now()` (`timestamptz`). Always real wall time. |
| **Browser time** | Toast timestamps, relative timers (`Xm ago`) | Display only on the operator dashboard | Browser local clock, corrected with `server_time_offset_ms` calculated on initial handshake. |

---

## 2. Core Scheduling & Lifecycle Rules

1. **Scheduling & Expiry Decoupled from Event Time:**
   - Expiry logic, cooldown checks, and notification dispatch (`catchup_max_age_s`, escalation `due_at`, and unacknowledged timers) MUST evaluate against **DB insertion time** (`alerts.received_at`), not `alerts.created_at` (event time).
   - Reason: When historical or simulated scenario footage is replayed (where `created_at` may be hours or weeks in the past), checking `created_at < now() - interval` would incorrectly flag newly ingested alerts as `STALE`, dropping valid notifications.
2. **Investigation & Correlation Use Event Time:**
   - Cross-camera journey correlation (Day 19), velocity calculation, and time-range search use **Event Time** (`created_at` / `timestamp`).
   - In offline test replay, simulated clock starts are synchronized across cameras to preserve topological travel time validity.
3. **Wall-Clock Rules (After-Hours):**
   - Temporal rules (e.g. after-hours restrictions) evaluate against the simulated event time in `file_offline` mode.
   - For `rtsp_live` scenario verification, rule definitions configure scenario-appropriate time windows (e.g. `00:00–23:59`) rather than altering the host system clock.
4. **Monotonicity & Non-Decreasing Guarantee:**
   - For any single camera, journaled event timestamps MUST be strictly non-decreasing (within a 1.0s tolerance for frame reordering).
   - No event timestamp may be in the future (`> now() + 5.0s`).
