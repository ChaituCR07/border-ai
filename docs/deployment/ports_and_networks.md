# Ports and Network Segmentation Topology

This document describes the container network topology, port exposures, firewall policies, and isolation rules for the Border-AI production stack.

---

## 1. Network Segmentation Architecture

To enforce defense-in-depth, Border-AI establishes three distinct internal Docker networks with zero cross-talk permitted except via dedicated intermediaries (ADR 0050):

```
                        PUBLIC / EXTERNAL
                               │
                       ┌───────▼────────┐
                       │  Nginx Proxy   │ (Publishes: 80, 443)
                       │  (Edge Gateway)│
                       └───────┬────────┘
                               │
                border-frontend-net (Bridge)
                               │
           ┌───────────────────┴───────────────────┐
           │                                       │
  ┌────────▼────────┐                     ┌────────▼────────┐
  │ Frontend (SPA)  │                     │ Backend (API/WS)│
  └─────────────────┘                     └────────┬────────┘
                                                   │
                                    border-data-net (Bridge, Internal)
                                                   │
              ┌───────────────────┬────────────────┴───────────────────┐
              │                   │                                    │
     ┌────────▼────────┐ ┌────────▼────────┐                  ┌────────▼────────┐
     │ Postgres (5432) │ │  Redis (6379)   │                  │ AI Engine / Sink│
     └─────────────────┘ └─────────────────┘                  └────────┬────────┘
                                                                       │
                                                        border-media-net (Bridge)
                                                                       │
                                                              ┌────────▼────────┐
                                                              │ MediaMTX Relay  │
                                                              └─────────────────┘
```

### Network Definitions
1. **`border-frontend-net`**: Connects Nginx reverse proxy to Web SPA and Backend API.
2. **`border-data-net`**: Isolated data persistence plane (`internal: true`). Only Backend, AI Engine, Sink, and Init jobs can communicate with Postgres and Redis.
3. **`border-media-net`**: RTSP video ingestion network linking MediaMTX relay, CCTV simulator, and AI Engine.

---

## 2. Port Exposure Matrix

Only the edge reverse proxy exposes published ports to the host network interface. All other ports remain reachable solely over internal Docker networks.

| Container | Service Role | Internal Port | Published Port | Scope | Access Restrictions |
|---|---|---|---|---|---|
| `nginx` | Edge Proxy / TLS | `80`, `443` | **`80`, `443`** | Public / Host | Open to client browsers and operators |
| `frontend` | Static Web SPA | `80` | *None* | `border-frontend-net` | Reached only via Nginx reverse proxy |
| `backend` | REST API & WS Gateway | `3000` | *None* | `border-frontend-net`, `border-data-net` | Reached only via Nginx reverse proxy |
| `ai-engine` | Video Pipeline & Metrics | `8001` | *None* | `border-media-net`, `border-data-net`, `border-frontend-net` | Reached only via Backend / Nginx internal proxy |
| `postgres` | SQL Database | `5432` | *None* | `border-data-net` | Strictly isolated; no host port publishing |
| `redis` | Cache & Message Broker | `6379` | *None* | `border-data-net` | Strictly isolated; no host port publishing |
| `mediamtx` | RTSP Relay | `8554` | *None* | `border-media-net` | Reached only by Engine and Simulator |
| `cctv-sim` | RTSP Simulator | *None* | *None* | `border-media-net` | Egress client only to MediaMTX |

---

## 3. Host Firewall & Egress Policies

When deploying on production Linux hosts:

### Ingress Rules
- Allow incoming TCP `80` (HTTP redirect) and `443` (HTTPS / WSS / MJPEG) on the host interface.
- Block external access to ports `5432`, `6379`, `3000`, `8001`, and `8554`.
- Never use `--net=host` on production deployments.

### Egress Rules
- Production containers execute with default zero external egress, except for one-shot `model-init` which may contact official HuggingFace / Google Cloud Storage mirrors if models are not pre-cached locally.
- In high-security air-gapped environments, model weights are mounted offline from `/data/models` with egress completely disabled.
