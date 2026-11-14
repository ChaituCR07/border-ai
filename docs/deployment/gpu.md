# GPU Deployment Guide (NVIDIA CUDA)

This guide documents deploying Border-AI with hardware-accelerated GPU inference using NVIDIA GPUs, CUDA 12.1, and the NVIDIA Container Toolkit.

---

## 1. Hardware & Driver Prerequisites

To leverage hardware acceleration on Linux or Windows WSL2:

- **NVIDIA GPU:** Pascal architecture or newer (Compute Capability 6.1+; e.g. GTX 1080, RTX 20/30/40 series, T4, A10, A100).
- **VRAM Recommendation:**
  - 1–2 Streams: Minimum 4 GB VRAM.
  - 4 Streams: Minimum 8 GB VRAM.
  - 8+ Streams: Minimum 16 GB VRAM.
- **NVIDIA Drivers:** Version `525.60.13` or newer.
- **NVIDIA Container Toolkit:** `nvidia-container-toolkit` package installed and configured as Docker runtime.

### Verifying Docker GPU Passthrough
```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

---

## 2. Launching Stack with GPU Acceleration

Launch using the GPU compose overlay (`docker-compose.gpu.yml`):

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### What `docker-compose.gpu.yml` Overrides
- Mounts NVIDIA GPU device reservations into `ai-engine`.
- Sets `DEVICE=cuda` and selects PyTorch CUDA 12.1 execution provider.
- Configures memory reservation and shared memory (`shm_size: 2gb`).

---

## 3. GPU VRAM & Throughput Benchmarks

Measured under Day 24 benchmark harness on NVIDIA RTX 3080 (10 GB VRAM):

| Scenario | Streams | Frame Rate | Inference Latency (p95) | VRAM Peak | Engine CPU Usage |
|---|---|---|---|---|---|
| Single Stream | 1 | 30 FPS | 11.2 ms | 1.8 GB | 14% |
| Multi-Camera Normal | 4 | 15 FPS | 14.6 ms | 3.4 GB | 28% |
| Multi-Camera Heavy | 8 | 15 FPS | 24.1 ms | 6.2 GB | 52% |
