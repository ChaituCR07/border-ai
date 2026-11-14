# Border-AI Production Deployment Guide

This guide details the single-command deployment, hardware run modes, and operational lifecycle of the Border-AI video intelligence platform using Docker Compose.

---

## 1. Quickstart (One Command Deployment)

From a fresh clone on any Docker-enabled host:

```bash
# 1. Clone the repository and navigate into project directory
git clone https://github.com/ChaituCR07/border-ai.git
cd border-ai

# 2. Execute automated quickstart provisioning
make quickstart
```

### What `make quickstart` Does:
1. Generates cryptographically secure, file-based secrets under `secrets/` (`scripts/gen_secrets.sh`).
2. Creates TLS certificates with Subject Alternative Names (SANs) under `certs/` (`scripts/gen_certs.sh`).
3. Validates the Docker Compose production specification (`docker-compose.yml`).
4. Builds multi-stage, non-root container images.
5. Executes one-shot bootstrap jobs: `db-init` (roles), `migrate` (schema), `model-init` (SHA-256 weight verification), and `bootstrap-admin`.
6. Starts all healthchecked services and reports the root administrative credentials.

---

## 2. Platform Access Endpoints

Once `make quickstart` completes, all traffic is routed through the hardened Nginx edge:

- **Command Center Web Dashboard:** `https://localhost` (or `https://localhost:8443`)
- **REST API Entrypoint:** `https://localhost/api`
- **Real-Time WebSocket Gateway:** `wss://localhost/api/ws`
- **Initial Administrator Password:** Displayed in terminal and recorded in `secrets/bootstrap_admin_password`.

> [!NOTE]
> The internal database (`5432`), Redis (`6379`), and AI engine metrics (`8001`) are isolated on internal Docker networks and **not** published to the public network.

---

## 3. Hardware Execution Modes

| Run Mode | Architecture | When to Use | Command |
|---|---|---|---|
| **Mode A: Full Containers (CPU)** | All services in Docker, CPU inference | Standard Linux/WSL2, CI, or systems without dedicated GPUs | `make compose-up` |
| **Mode B: Full Containers (NVIDIA CUDA)** | All services in Docker, GPU passthrough | Linux or WSL2 with NVIDIA drivers & Container Toolkit | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` |
| **Mode C: Hybrid (macOS Apple Silicon)** | Infra/backend in Docker, engine native with MPS | macOS workstations seeking maximum local M-series GPU performance | `docker compose -f docker-compose.yml -f docker-compose.hybrid.yml up -d` |

Detailed instructions for macOS hybrid mode are documented in [`docs/deployment/macos_hybrid.md`](macos_hybrid.md).

---

## 4. Stack Management Commands

```bash
# View real-time status of all containers
make compose-ps

# Follow aggregated logs across services
make compose-logs

# Run automated smoke test against edge
make smoke-compose

# Execute complete deployment hardening & isolation audit
make test-compose

# Create encrypted database & snapshot backup
make backup

# Stop the platform gracefully
make compose-down
```
