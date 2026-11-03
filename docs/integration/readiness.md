# Integration Readiness Audit & Baseline Metrics

This report documents the Day 21 pre-flight system audit, configuration inventory, port assignments, and baseline numbers as required by Task 0.

---

## 1. Baseline Numbers (Start of Day 21)

| Metric | Measured Value | Source / Command |
|---|---|---|
| Git commits | 431 | `git rev-list --count HEAD` |
| ADR documents | 31 | `ls docs/decisions \| grep -c '\.md'` |
| Database migrations | 7 | `ls database/migrations \| grep -c '\.sql'` |
| Backend unit tests | 135 passed (23 files) | `npm --prefix backend test -- tests/unit/` |
| Frontend compilation | Clean (0 errors) | `npm --prefix frontend run typecheck` |
| Backend compilation | Clean (0 errors) | `npm --prefix backend run build` |

---

## 2. Configuration Inventory

| Configuration File | Primary Consumer | Purpose |
|---|---|---|
| `configs/rules.json` | `ai-engine` (Behaviour Engine) | Detection & behaviour rules (zones, line crossing, loitering, after-hours) |
| `configs/threat_thresholds.json` | `ai-engine` & `backend` | Severity score boundaries (LOW 0-29, MED 30-59, HIGH 60-79, CRIT 80-100) |
| `configs/camera_topology.json` | `backend` (Correlation Module) | Distance matrix and travel-time bounds across border cameras |
| `configs/camera_topology.demo.json` | `backend` / Live Rehearsal | Scaled topology (÷10 travel times) for live demo execution |
| `configs/correlation.json` | `backend` (Correlation Module) | Link plausible limits, anomaly thresholds, Re-ID weights |
| `configs/notifications.json` | `backend` (Notification Outbox) | Production notification profiles, channels, escalation rules |
| `configs/notifications.demo.json` | `backend` (Test Scenarios) | Short cooldowns (5s) and quick escalation (15s) for integration tests |
| `configs/mediamtx.yml` | MediaMTX RTSP Server | RTSP server paths `cam01`–`cam04` and auth policies |
| `.env.integration` | Compose & Process Runner | Unified integration test env vars with canary secrets |

---

## 3. Port Map & Network Allocations

| Service | Port | Protocol | Purpose |
|---|---|---|---|
| PostgreSQL | 5432 | TCP | Relational storage (`border_ai_integration` DB) |
| Redis | 6379 | TCP | Stream bus (`events`, `alerts`, `dead`) & heartbeats |
| MediaMTX RTSP | 8554 | TCP | RTSP camera stream ingest & publisher |
| Mailpit SMTP | 1025 | TCP | Outbox email delivery catch-all |
| Mailpit Web/API | 8025 | HTTP | Mailpit web UI and REST search API |
| Backend API | 4000 | HTTP / WS | Express REST API and WebSocket `/api/ws` |
| AI Engine MJPEG | 8001 | HTTP | Annotated live video stream server |
| Frontend UI | 5173 | HTTP | Vite React operator dashboard |

---

## 4. Credentials Path & Canary Tokens

To verify zero-leakage promises, `.env.integration` uses distinctive canary strings:
- RTSP Publisher: `rtsp_pub_user` / `zq9canaryRtspPub`
- RTSP Reader: `rtsp_read_user` / `zq9canaryRtspRead`
- PostgreSQL: `postgres` / `zq9canaryPg`
- JWT Secret: `zq9canaryJwtSecretKey`
- Mailpit SMTP Auth: `smtp_user` / `zq9canarySmtp`

The automated conformance scanner (`scripts/conformance/scan.py`) audits all logs, databases, redis keys, api outputs, and email payloads to assert none of these canary secrets leak into logs, payloads, or UI.

---

## 5. Storage & Directory Structure

- `data/snapshots/`: Alert JPEG snapshots with retention policies.
- `data/journal/`: Local append-only JSONL event journal (`events.jsonl`).
- `artifacts/tmp/`: Run artifacts, timeline outputs, and reconciliation logs.
- `footage/`: Ground-truth test clips for Scenarios S0–S3 with `footage/MANIFEST.md`.
