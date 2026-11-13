# Attack Surface Register & Entry Point Inventory

**Date:** 2026-11-13  
**Scope:** Border-AI Video Intelligence Platform  

---

## 1. Entry Point Inventory

| Surface ID | Component | Port / Path | Protocol | Current Baseline | Target Security Posture |
|---|---|---|---|---|---|
| **S-01** | REST API | `:4000/api/*` | HTTP / JSON | Basic stub auth | EdDSA JWT Bearer token + Deny-by-default RBAC |
| **S-02** | Auth Endpoints | `:4000/api/auth/*` | HTTP / JSON | None | Rate-limited, anti-enumeration, Argon2id, HttpOnly cookie |
| **S-03** | OpenAPI Docs | `:4000/docs`, `/openapi.json` | HTTP / HTML / JSON | Open | Restricted in production (admin/dev-only) |
| **S-04** | Live Event Stream | `:4000/api/ws` | WebSocket | Origin header check | Origin check + Single-use 128-bit ticket |
| **S-05** | Evidence Storage | `:4000/api/snapshots/*` | HTTP / Static | Safe-path checks | `evidence:view` permission + Viewer person redaction |
| **S-06** | Engine MJPEG Stream | `:8001/cam/*.mjpg` | HTTP / MJPEG | Open access | Signed EdDSA stream tokens (`typ=stream+jwt`), 60s TTL |
| **S-07** | Engine Telemetry | `:8001/metrics.json`, `/healthz` | HTTP / JSON | Open access | Bound to localhost/internal network; token required |
| **S-08** | Message Broker | `:6379` | RESP (Redis) | Open / default | Redis ACL users (engine, sink, gateway, api); default disabled |
| **S-09** | Relational Database | `:5432` | PostgreSQL | Single API role | Per-service least-privilege roles (`border_engine`, `border_sink`, `border_api`) |
| **S-10** | Video Ingest Server | `:8554` | RTSP / RTMP | Basic authentication | Protected RTSP credentials via AES-256-GCM vault |
| **S-11** | SMTP Mailpit | `:8025` | HTTP / Web | Dev UI open | Development environment only; never exposed in production |
| **S-12** | Frontend SPA | `:5173` | HTTP / React | Dev server | In-memory token storage, Strict CSP, SameSite cookies |

---

## 2. Ingress & Egress Data Flow Matrix

```
[Camera RTSP] ----(RTSP:8554)----> [MediaMTX] ----(RTSP)----> [Inference Engine]
                                                                     |
                                                                (Redis XADD)
                                                                     v
[Web Browser] <----(HTTP:4000)----> [Fastify API] <---(Pub/Sub)--- [Redis]
      |                                    |                         ^
      | (MJPEG Stream + Token)             v                         |
      +------------(HTTP:8001)----> [Engine Server]            [Worker Sink]
                                           |                         |
                                           +--(Insert/Select)--------+
                                                        |
                                                        v
                                                  [PostgreSQL]
```

---

## 3. Security Boundary Controls

### 3.1 Network Controls
- Engine port `:8001` and Redis `:6379` are bound to internal network interfaces only (`127.0.0.1` or docker bridge network).
- Fastify API acts as the single external gateway for all user and client interactions.

### 3.2 Protocol Safeguards
- Strictly typed JSON request payloads validated using Zod / Fastify type provider schemas.
- Prototype pollution defenses enabled on Fastify body parser (`protoAction: 'remove'`, `constructorAction: 'remove'`).
- Maximum request payload restricted to 1 MB globally, with auth endpoints capped at 1 KB.
