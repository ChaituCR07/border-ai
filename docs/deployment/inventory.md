# Deployment Inventory & Service Specification

This document provides a comprehensive operational inventory of all services, processes, networks, volumes, secrets, and run modes for the Border-AI platform.

---

## 1. Service Matrix

| Service | Base Image | Role | Networks | Published Ports | Healthcheck |
|---|---|---|---|---|---|
| `nginx` | `nginxinc/nginx-unprivileged:1.27-alpine` | TLS edge, reverse proxy, HTTP/2 termination, security headers | `edge`, `app` | **443** (HTTPS), **80** (HTTP redirect) | `wget --no-check-certificate -qO- https://127.0.0.1:8443/healthz` |
| `frontend` | `nginxinc/nginx-unprivileged:1.27-alpine` | Serves production Vite SPA static bundle | `app` | None (Internal `:8080`) | `wget -qO- http://127.0.0.1:8080/` |
| `backend` | `node:22-bookworm-slim` | REST API, WebSocket gateway, notification worker, audit | `app`, `data`, `egress` | None (Internal `:4000`) | Node HTTP fetch `/api/health` |
| `ai-engine` | `python:3.11-slim-bookworm` (CPU / CUDA) | Ingestion, YOLOv8 detection, ByteTrack, spatial rules, ANPR, MJPEG stream | `app`, `data`, `media`, `egress`* | None (Internal `:8001`) | `python -m engine.healthcheck` |
| `sink` | `python:3.11-slim-bookworm` | Redis Streams consumer persisting events to PostgreSQL | `data` | None | Process monitoring |
| `postgres` | `postgres:16-bookworm` | Relational store (events, alerts, watchlist, users, audit) | `data` | None (Dev: `127.0.0.1:5432`) | `pg_isready -U postgres -d border_ai` |
| `redis` | `redis:7.4-bookworm` | Redis Streams pipeline, heartbeat status keys, ACL security | `data` | None (Dev: `127.0.0.1:6379`) | `redis-cli --user healthcheck ping` |
| `mediamtx` | `bluenviron/mediamtx:1.9.3-ffmpeg` | RTSP relay for simulated/local camera streams | `media` | None (Dev: `127.0.0.1:8554`) | RTSP port ready |
| `retention` | `node:22-bookworm-slim` | Scheduled purge of expired events, snapshots, and audit | `data` | None | Process / cron loop |
| `db-init` | `node:22-bookworm-slim` | One-shot job: provisions DB roles and privileges | `data` | None | Exits 0 on completion |
| `migrate` | `node:22-bookworm-slim` | One-shot job: executes forward-only schema migrations | `data` | None | Exits 0 on completion |
| `model-init` | `python:3.11-slim-bookworm` | One-shot job: verifies model hashes from `models.lock.json` | `egress` | None | Exits 0 on completion |
| `bootstrap-admin` | `node:22-bookworm-slim` | One-shot job: creates initial root administrator account | `data` | None | Exits 0 on completion |
| `mailpit` (demo) | `axllent/mailpit:v1.20` | Local SMTP sink for mock alert email deliveries | `app` | None (Dev: `127.0.0.1:8025`) | Web UI `:8025` |
| `cctv-sim` (demo) | `python:3.11-slim-bookworm` | Synthetic video feeder simulating live RTSP camera feeds | `media` | None | FFmpeg stream loop |

`*` `egress` network is enabled on `ai-engine` when connecting to external physical RTSP cameras.

---

## 2. Secrets Inventory

All secrets are provisioned via file mounts (`/run/secrets/*`) and read through the `*_FILE` convention:

| Secret Name | Consumer(s) | Description |
|---|---|---|
| `pg_admin_password` | `postgres`, `migrate`, `db-init` | Superuser password for database initialization and migrations |
| `pg_api_password` | `db-init`, `backend` | Password for least-privilege `border_api` database role |
| `pg_engine_password` | `db-init`, `ai-engine` | Password for least-privilege `border_engine` database role |
| `pg_sink_password` | `db-init`, `sink` | Password for least-privilege `border_sink` database role |
| `pg_retention_password` | `db-init`, `retention` | Password for least-privilege `border_retention` database role |
| `redis_acl` | `redis` | Production ACL file with SHA-256 hashed passwords |
| `redis_engine_password` | `ai-engine` | Password for `engine` Redis user (XADD to streams) |
| `redis_sink_password` | `sink` | Password for `sink` Redis user (XREADGROUP on streams) |
| `redis_gateway_password`| `backend` | Password for `gateway` Redis user (XREAD on alerts) |
| `redis_api_password` | `backend` | Password for `api` Redis user (GET status keys) |
| `redis_healthcheck_password` | `redis` healthcheck | Password for minimal `healthcheck` user (+ping only) |
| `jwt_private_key` | `backend` | PKCS#8 Ed25519 private key for signing access tokens |
| `master_key` | `backend`, `ai-engine` | 32-byte AES-256-GCM master key for camera credentials |
| `password_pepper` | `backend` | Cryptographic pepper applied during Argon2id hashing |
| `smtp_password` | `backend` | Password for outbound transactional email notifications |
| `internal_token` | `backend`, `ai-engine` | Shared bearer token for engine internal metrics scraping |
| `mediamtx_publish_password` | `cctv-sim`, `mediamtx` | RTSP publish authentication for simulated cameras |
| `mediamtx_read_password` | `ai-engine`, `mediamtx` | RTSP read authentication for camera streams |
| `bootstrap_admin_password` | `bootstrap-admin` | Initial password for first administrative account setup |

---

## 3. Persistent Volumes

| Volume Name | Mounted At | Written By | Read By | Purpose |
|---|---|---|---|---|
| `pgdata` | `/var/lib/postgresql/data` | `postgres` | `postgres` | Relational database storage |
| `redisdata` | `/data` | `redis` | `redis` | Redis AOF and RDB persistence |
| `snapshots` | `/data/snapshots` | `ai-engine` | `backend`, `retention` | Cropped incident detections & evidence images |
| `journal` | `/data/journal` | `ai-engine` | `ai-engine` | Local WAL journal buffering during network outages |
| `models` | `/models` | `model-init` | `ai-engine` | Pinned YOLOv8, PaddleOCR, and ONVIF model weights |

---

## 4. Network Segmentation

```text
[ Internet / Clients ]
         │
    (Port 443 / 80)
         ▼
    ┌─────────┐
    │  nginx  │ ◄─── edge network (publicly exposed)
    └────┬────┘
         │
    (internal)
         ├───────────────────────────────────────────────┐
         ▼                                               ▼
   ┌───────────┐                                   ┌───────────┐
   │ frontend  │ (app network)                     │  backend  │ (app, data, egress networks)
   └───────────┘                                   └─────┬─────┘
                                                         │
                                        ┌────────────────┴────────────────┐
                                        ▼                                 ▼
                                  ┌───────────┐                     ┌───────────┐
                                  │ postgres  │ (data network)      │   redis   │ (data network)
                                  └─────▲─────┘                     └─────▲─────┘
                                        │                                 │
                                  ┌─────┴─────┐                     ┌─────┴─────┐
                                  │   sink    │                     │ ai-engine │ (app, data, media networks)
                                  └───────────┘                     └─────▲─────┘
                                                                          │
                                                                    ┌─────┴─────┐
                                                                    │ mediamtx  │ (media network)
                                                                    │ cctv-sim  │
                                                                    └───────────┘
```

---

## 5. Execution Modes

- **Mode A: Full Containers (CPU):** Suitable for standard x86_64/arm64 Linux hosts, CI environments, and demonstrations without dedicated GPU hardware.
- **Mode B: Full Containers (NVIDIA CUDA):** Leverages `docker-compose.gpu.yml` for Linux/WSL2 hosts with NVIDIA GPUs via NVIDIA Container Toolkit.
- **Mode C: Hybrid (macOS / Apple Silicon):** Infrastructure and web services run in Docker; Python `ai-engine` runs natively utilizing Metal Performance Shaders (MPS) for maximal throughput.
