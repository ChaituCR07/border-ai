# Container Resource Allocations & Capacity Planning

This document details container CPU, memory limits, storage volumes, and capacity thresholds for the Border-AI Docker deployment.

---

## 1. Resource Limits & Reservations

To prevent "noisy neighbor" starvation and protect host stability, every container is provisioned with explicit `cpus` and `memory` limits in `docker-compose.yml`:

| Service | Memory Limit | Memory Reservation | CPU Limit | Rationale |
|---|---|---|---|---|
| `postgres` | 2048 MB | 512 MB | 2.0 cores | Shared buffers, query cache, spatial indexes |
| `redis` | 512 MB | 128 MB | 1.0 cores | In-memory message brokers, stream queues, rate limits |
| `backend` | 1024 MB | 256 MB | 2.0 cores | Prisma ORM, WebSocket gateway, auth crypto |
| `ai-engine` (CPU) | 4096 MB | 1024 MB | 4.0 cores | Video decoding, YOLO/ANPR tensor operations |
| `ai-engine` (GPU) | 6144 MB | 2048 MB | 4.0 cores | VRAM staging, high-throughput batching |
| `nginx` | 256 MB | 64 MB | 1.0 cores | Event-driven reverse proxy, SSL termination |
| `frontend` | 128 MB | 32 MB | 0.5 cores | Static unprivileged Nginx asset server |
| `mediamtx` | 512 MB | 128 MB | 1.0 cores | RTSP/WebRTC multiplexing |
| `sink` | 256 MB | 64 MB | 0.5 cores | Lightweight batch event persistence |

---

## 2. Storage Volume Sizing Recommendations

| Volume Name | Mount Point | Estimated Growth | Recommended Disk |
|---|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | ~1 GB / month (1M events) | 50–100 GB NVMe |
| `snapshots_data` | `/var/lib/border-ai/snapshots` | ~15 GB / month (4 cameras, 15 FPS) | 250–500 GB NVMe / SSD |
| `model_cache` | `/root/.cache` | ~1.5 GB static | 10 GB |
| `redis_data` | `/data` | < 100 MB transient | 5 GB |
