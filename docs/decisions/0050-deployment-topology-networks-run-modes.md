# ADR 0050: Production Deployment Topology, Networks, and Run Modes

## Status
Accepted

## Context
Until Day 26, the Border-AI platform operated in a hybrid development environment (ADR 0001) where backing services (PostgreSQL, Redis, MediaMTX) ran in Docker Compose while application services (Fastify backend, Vite frontend, Python AI engine, event sink) executed as local host processes. 

For production release, the complete system must be orchestratable via a single command (`docker compose up` / `make quickstart`), strictly maintain network isolation, enforce least privilege, prevent secret exposure, and support distinct hardware environments (x86_64, CUDA GPUs, and Apple Silicon).

## Decision

1. **Service Architecture & Segmentation:**
   - **Nginx Edge:** The sole service publishing external host ports (`443` HTTPS and `80` HTTP redirect). Terminates TLS 1.3/1.2, enforces HTTP/2 multiplexing, security headers, unbuffered MJPEG streaming, and WebSocket connection upgrade.
   - **Internal Network Segregation:**
     - `edge`: Connects external traffic to Nginx only.
     - `app` (internal): Connects Nginx, frontend static server, backend REST/WS, and AI engine metrics.
     - `data` (internal): Connects backend, AI engine, sink, retention worker to PostgreSQL and Redis. Backing stores publish NO host ports in production.
     - `media` (internal): Isolates RTSP stream ingestion, MediaMTX relay, and CCTV simulation.
     - `egress`: Restricted outbound network for external camera feeds and transactional SMTP.
   - **Deterministic Startup Order:**
     `postgres` & `redis` (healthy) $\rightarrow$ `db-init` (roles/grants) $\rightarrow$ `migrate` (schema) $\rightarrow$ `model-init` (weights) $\rightarrow$ `bootstrap-admin` (root admin) $\rightarrow$ `backend`, `sink`, `ai-engine` (healthy) $\rightarrow$ `frontend` $\rightarrow$ `nginx`.

2. **Run Modes:**
   - **Mode A (Full Containers, CPU):** Default out-of-the-box configuration for any Docker host. Runs lightweight CPU-optimized YOLOv8 and PaddleOCR pipelines.
   - **Mode B (Full Containers, NVIDIA GPU):** Activated via `docker-compose.gpu.yml` reservation overlay, utilizing CUDA-accelerated PyTorch builds.
   - **Mode C (Hybrid, macOS Apple Silicon):** Supported configuration where database, Redis, backend, frontend, and Nginx execute in Docker containers, while `ai-engine` runs natively on macOS to exploit Apple Silicon unified memory and MPS GPU acceleration.

## Consequences

- Direct access to databases, Redis streams, and internal MJPEG engine ports from outside the host network is strictly prevented.
- Startup sequencing is fully deterministic with zero race conditions between migration execution and service readiness.
- Deployers on Apple Silicon retain full native MPS hardware acceleration without VM virtualization penalties.
