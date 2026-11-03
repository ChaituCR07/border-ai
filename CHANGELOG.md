# Changelog

All notable changes to the Border-AI Video Intelligence Platform are documented in this file.

## [v0.3-week3] - 2026-11-03
### Week 3 Milestone: Productization, Dashboards & Full-System Integration

#### Added
- **Full-System Integration Harness:** Acceptance test runner executing Scenarios S0 (Negative Control), S1 (Night Intrusion), S2 (Watchlist Vehicle), and S3 (Cross-Camera Journey) with 3/3 deterministic repeatability (`tests/integration/harness/`).
- **MediaMTX RTSP Streaming & CCTV Simulator:** Automated FFmpeg supervisor with clock burn-in overlay, TCP transport, credential masking, and fault injection (`scripts/sim/cctv_sim.py`).
- **Engine Heartbeat & Health Telemetry:** Redis TTL heartbeat publisher, camera classification (`ONLINE`, `RECONNECTING`, `STALLED`, `OFFLINE`), and unified backend status endpoint (`/api/system/status`).
- **Operator System Health Chip:** Frontend header component with real-time status pill and detailed component telemetry modal (`SystemStatusChip.tsx`).
- **Reconciliation Correctness Oracle:** Tool auditing 12 consistency invariants across journals, Redis streams, PostgreSQL, WebSocket, and Mailpit (`scripts/reconcile.py`).
- **Chaos & Failure Testing:** Fault injection harness verifying zero loss across Redis, PostgreSQL, SMTP, and camera disconnections (`scripts/chaos/inject_fault.py`).
- **Privacy & Conformance Scanner:** Automated scanner auditing logs and payloads for canary secrets, biometric float vectors, and PII leaks (`scripts/conformance/scan.py`).
- **Architecture Decision Records:** Added ADR 0032 (Integration Test Architecture), ADR 0033 (Heartbeat & System Status), and ADR 0034 (Reconciliation Oracle).

#### Fixed
- **Time Basis Bug (INT-001):** Decoupled notification catch-up horizon and timers from simulated event times using `alerts.received_at TIMESTAMPTZ NOT NULL DEFAULT now()` (Migration 008).
- **RTSP Parity Latency (INT-002):** Configured MediaMTX TCP transport and zero-latency tuning to prevent frame buffer lag.
- **Scenario 1 Card Polish:** Rendered formatted event checklists with tick marks (`✓`) in the operator alert drawer.
