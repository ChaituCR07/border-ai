# Integration Bug Log & Triage (Task 12)

This log records bugs identified during integration and scenario acceptance testing, root causes, severity, fixes, and regression test coverage.

| Bug ID | Found By | Symptom | Root Cause | Severity | Fix | Regression Test |
|---|---|---|---|---|---|---|
| **INT-001** | S2 Time-Basis Audit | Replayed alerts in offline simulated mode sent zero email notifications | Notification planner evaluated catch-up horizon (`catchup_max_age_s`) against `a.created_at` (simulated event time in the past), dropping replayed alerts as stale | **P0** | Added `alerts.received_at TIMESTAMPTZ NOT NULL DEFAULT now()` (Migration 008); planner queries `COALESCE(a.received_at, a.created_at)` | `backend/tests/unit/notifications-planner.test.ts` |
| **INT-002** | RTSP Parity Check | In live RTSP streaming, event detection shifted by 1.2s due to TCP GOP buffering | Video frame queue in RTSP reader accumulated latency | **P1** | Set MediaMTX `protocols: [tcp]`, FFmpeg `-tune zerolatency` and engine latest-frame queue drain | `tests/integration/test_scenario3_journey.py` |
| **INT-003** | Stalled Camera Simulation | Browser unable to differentiate between stalled CCTV feed and normal slow frame rate | Stream socket remained open, preventing HTML5 error event | **P1** | Heartbeat daemon detects `now - last_frame_ts > 10.0s`, marks camera `STALLED` in Redis; dashboard displays amber pause indicator | `tests/test_heartbeat.py` |
