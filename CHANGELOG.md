# Changelog

All notable changes to the Border-AI Video Intelligence Platform are documented in this file.

## [v1.0.0] - 2026-11-15
### Milestone: Production Release, Hardening & Portfolio Delivery

#### Added
- **Production Docker Compose Deployment (Day 27):** Single-command stack launch (`make quickstart`) orchestrating 10 containers (frontend, backend, ai-engine, postgres, redis, sink, retention, sim, mediamtx, nginx). Non-root multi-stage containers, zero secrets in images/env (ADR 0052), and 3-tier internal network isolation (ADR 0050).
- **Hardened Edge Proxy:** Nginx reverse proxy terminating TLS 1.3/HTTP/2, unbuffered MJPEG streaming, WebSocket forwarding, and query-free access logs (`$uri` instead of `$request_uri`).
- **Hardware Run Modes:** Support for Mode A (Linux CPU), Mode B (NVIDIA CUDA via `docker-compose.gpu.yml`), and Mode C (macOS Hybrid with Apple Silicon MPS acceleration).
- **Disaster Recovery & Data Retention:** Automated AES-256-CBC encrypted backups (`scripts/backup.sh` / `scripts/restore.sh`) and automated data retention service purging expired records and snapshots.
- **Resilience Test Suite:** Verified R1–R12 fault-injection matrix with zero telemetry loss during database and Redis crashes (`docs/deployment/resilience_results.md`).
- **Security Hardening (Day 26):** Full STRIDE threat model (ADR 0048), OWASP ASVS 4.0 Level 2 compliance (30/30 automated controls passed), least-privilege RBAC, Argon2id passwords, Ed25519 JWTs, rotating refresh cookies, and SHA-256 hash-chained audit log.
- **Scientific Evaluation Harness (Days 22–25):** 1,000-resample bootstrap 95% confidence intervals, frozen deterministic subsets (COCO-1000, BDD100K-500, MOT17 static splits), dual-mode evaluation, ANPR CER/WER metrics, and false-positive verification across 4.25 camera-hours of uneventful footage (0 FP alerts $\ge\text{HIGH}$).
- **Release Documentation & Deliverables (Day 28):** Architectural diagrams (`architecture.svg`, `system-flow.svg`, `database-schema.svg`, `deployment.svg`), static Redoc API documentation, WebSocket protocol spec, 5-minute video storyboard with SRT captions, capability matrix, detailed technical limitations, responsible use policy, and portfolio brief.

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
