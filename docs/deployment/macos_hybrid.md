# macOS Apple Silicon Hybrid Deployment Guide

This guide explains how to run Border-AI on macOS (Apple Silicon M1/M2/M3/M4) in **Hybrid Mode (Mode C)** to leverage native Metal Performance Shaders (MPS) GPU acceleration.

---

## 1. Why Hybrid Mode?

Docker on macOS runs inside a Linux virtual machine (HyperKit, Virtualization.framework). Because Apple Silicon does not expose Metal GPU acceleration to Linux guests inside Docker, running PyTorch inside a Linux container on macOS defaults to CPU-only execution.

**Hybrid Mode (Mode C)** provides the best of both worlds:
- **Infrastructure & Services** (Postgres, Redis, Backend, Frontend, Nginx, MediaMTX) run in Docker Compose with complete isolation.
- **AI Inference Engine** runs natively on the macOS host, utilizing PyTorch `mps` (Metal) acceleration directly with unified memory.
- `docker-compose.hybrid.yml` maps ports so the native host engine connects transparently to the containerized database, Redis, and RTSP relay.

---

## 2. Launching Hybrid Mode

### Step 1: Start Containerized Infrastructure
```bash
# Start infrastructure and web stack with hybrid overrides
docker compose -f docker-compose.yml -f docker-compose.hybrid.yml up -d
```

In this mode:
- `postgres` (port `5432`), `redis` (port `6379`), and `mediamtx` (port `8554`) are mapped to `127.0.0.1` on the macOS host.
- A lightweight container stub runs inside Compose to satisfy internal routing.

### Step 2: Start Native AI Engine with MPS
```bash
# In a separate terminal or background session:
cd engine

# Set environment pointing to localhost services
export DB_HOST=127.0.0.1
export REDIS_HOST=127.0.0.1
export MEDIAMTX_HOST=127.0.0.1
export DB_PASSWORD_FILE=../secrets/engine_db_password
export DEVICE=mps

# Run native pipeline supervisor
python3 -m engine.main
```

---

## 3. Performance Comparison (macOS M-Series)

| Configuration | Inference Latency (YOLOv8x p95) | 4 Streams FPS | Thermal / Power |
|---|---|---|---|
| Full Docker (Linux CPU inside VM) | ~68 ms | 14.2 FPS (near CPU ceiling) | High CPU core load |
| **Hybrid Mode (Host MPS Metal)** | **~13 ms** | **30.0 FPS (sustained)** | Low CPU, unified GPU memory |
