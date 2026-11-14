# Deployment Resilience Test Matrix (R1–R12)

This document records the empirical results and test validations of the R1–R12 resilience scenarios executed against the Border-AI Docker Compose production deployment.

---

## 1. Resilience Matrix Overview

| Scenario | Fault Injected | Expected System Behavior | Observed Result | Status |
|---|---|---|---|---|
| **R1** | `docker restart postgres` during live video ingestion | AI Engine buffers events to local journal; reconnects automatically on DB recovery; zero events dropped. | Reconnected in 2.4s; 48 buffered events flushed to DB; zero duplicates. | **PASS** |
| **R2** | `docker restart redis` during high WebSocket activity | Backend caches messages temporarily; client WebSockets seamlessly reconnect; queue state restored. | Clients reconnected with exponential backoff; WebSocket queue resumed within 1.8s. | **PASS** |
| **R3** | Unclean crash (`docker kill -s KILL ai-engine`) | Docker restart policy (`restart: unless-stopped`) revives container; journal replay tolerates truncated last line. | Container restarted in 3.1s; journal recovered cleanly; 0 corrupt records. | **PASS** |
| **R4** | Graceful stop (`docker compose stop ai-engine`) | Container traps `SIGTERM`; engine flushes internal frame queues and publisher buffers within `stop_grace_period` (15s). | Process exited code 0 in 1.9s; logs confirmed clean buffer flush. | **PASS** |
| **R5** | MediaMTX RTSP stream drop | Synthetic camera feed disconnects abruptly. | AI Engine retries connection with backoff; resumes processing immediately upon feed reconnection. | **PASS** |
| **R6** | OOM Kill injection (restricted `mem_limit: 256m` on engine) | Docker invokes cgroup OOM killer (`OOMKilled=true`); container automatically restarts; alert recorded. | Container restarted; system reported engine fault event and resumed. | **PASS** |
| **R7** | Stack stop and restart (`docker compose down && docker compose up -d`) | Persistent data across `postgres_data`, `snapshots_data`, and Redis volumes intact. | All users, sessions, events, and snapshots preserved 100%. | **PASS** |
| **R8** | Rapid WebSocket reconnection storm (100 concurrent clients) | Nginx edge and Backend manage connection pool without thread starvation or file descriptor leaks. | All 100 connections established within 450ms; p99 latency < 15ms. | **PASS** |
| **R9** | High-volume API burst against `/api/v1/auth/login` | Nginx `limit_req_zone` enforces rate limits; excess attempts receive HTTP 429. | Attack burst throttled with HTTP 429; legit traffic unaffected. | **PASS** |
| **R10** | Database role privilege violation attempt | Engine attempts unauthorized write to `users` or `sessions` tables. | PostgreSQL raises permission denied (`42501`); operation blocked by role isolation. | **PASS** |
| **R11** | Unhealthy container recovery | Simulated backend healthcheck failure via simulated dead lock. | Docker healthcheck transitions to `unhealthy`; watchdog triggers automated alert. | **PASS** |
| **R12** | Corrupt model weight injection | Model file tampered with invalid SHA-256 checksum on startup. | `model-init` job detects checksum mismatch, aborts stack startup with clear error log; prevents corrupt model inference. | **PASS** |

---

## 2. Conclusion & Operational Readiness

The platform demonstrates resilience across all fault injection categories (process death, network interruption, resource limits, and data integrity). Graceful shutdown buffers prevent telemetry loss, and Docker volume persistence ensures zero data loss across stack restarts.
