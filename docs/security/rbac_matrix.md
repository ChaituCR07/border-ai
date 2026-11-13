# Role-Based Access Control (RBAC) Matrix

**Generated On:** 2026-11-13T17:39:19.791Z
**Source of Truth:** `backend/src/security/policy.ts`

---

## 1. Role to Permission Mapping

| Permission | Description | VIEWER | OPERATOR | INVESTIGATOR | ADMIN |
|---|---|:---:|:---:|:---:|:---:|
| `live:view` | Live MJPEG video stream viewing | ✓ | ✓ | ✓ | ✓ |
| `alerts:view` | Query alerts and read threat summaries | ✓ | ✓ | ✓ | ✓ |
| `alerts:ack` | Acknowledge pending threat alerts | ✗ | ✓ | ✓ | ✓ |
| `alerts:resolve` | Resolve threat alerts with operational disposition | ✗ | ✓ | ✓ | ✓ |
| `events:view` | Search historical events and review facets | ✓ | ✓ | ✓ | ✓ |
| `evidence:view` | Access unredacted forensic evidence and person snapshots | ✗ | ✓ | ✓ | ✓ |
| `investigation:journey` | Multi-camera vehicle journey tracking | ✗ | ✓ | ✓ | ✓ |
| `investigation:person_search` | Attribute and biometric search on persons | ✗ | ✗ | ✓ | ✓ |
| `investigation:sequence` | Temporal-spatial camera sequence correlation | ✗ | ✗ | ✓ | ✓ |
| `export:csv` | Export forensic intelligence to CSV format | ✗ | ✗ | ✓ | ✓ |
| `watchlist:view` | Read target license plates and identity descriptions | ✗ | ✗ | ✓ | ✓ |
| `watchlist:write` | Register, modify, or delete watchlist entries | ✗ | ✗ | ✓ | ✓ |
| `config:read` | View system configuration, thresholds, and topologies (read-only) | ✗ | ✗ | ✓ (*Limited*) | ✓ |
| `config:write` | Update detection rules, thresholds, and notification policies | ✗ | ✗ | ✗ | ✓ |
| `cameras:view` | Inspect camera hardware registry and status | ✓ | ✓ | ✓ | ✓ |
| `cameras:write` | Add, edit, or decommission camera devices | ✗ | ✗ | ✗ | ✓ |
| `topology:write` | Update spatial adjacency and corridor links | ✗ | ✗ | ✗ | ✓ |
| `notifications:admin` | Configure notification delivery, test, and retry queues | ✗ | ✗ | ✗ | ✓ |
| `users:manage` | Create users, modify roles, reset passwords, disable accounts | ✗ | ✗ | ✗ | ✓ |
| `audit:view` | Query immutable audit log and verify cryptographic hash chain | ✗ | ✗ | ✗ | ✓ |
| `retention:run` | Trigger automated retention pruning tasks | ✗ | ✗ | ✗ | ✓ |
| `system:status` | Query high-level telemetry and node status | ✓ | ✓ | ✓ | ✓ |
| `system:detail` | Access deep queue diagnostics, redis memory, and internal metrics | ✗ | ✗ | ✗ | ✓ |
| `realtime:subscribe` | Subscribe to realtime WebSocket event and alert streams | ✓ | ✓ | ✓ | ✓ |

---

## 2. Endpoint to Permission Register

| HTTP Method | Endpoint Path | Required Permission | Public / Protected |
|---|---|---|:---:|
| GET | `/health` | `public` | Public |
| GET | `/ready` | `public` | Public |
| GET | `/.well-known/jwks.json` | `public` | Public |
| POST | `/api/auth/login` | `public` | Public |
| POST | `/api/auth/refresh` | `public` | Public |
| POST | `/api/auth/logout` | `system:status` | Protected |
| POST | `/api/auth/logout-all` | `system:status` | Protected |
| GET | `/api/auth/me` | `system:status` | Protected |
| POST | `/api/auth/change-password` | `system:status` | Protected |
| GET | `/api/cameras` | `cameras:view` | Protected |
| POST | `/api/cameras` | `cameras:write` | Protected |
| GET | `/api/cameras/:id` | `cameras:view` | Protected |
| PUT | `/api/cameras/:id` | `cameras:write` | Protected |
| GET | `/api/events` | `events:view` | Protected |
| GET | `/api/events/:id` | `events:view` | Protected |
| GET | `/api/events/:id/context` | `events:view` | Protected |
| GET | `/api/alerts` | `alerts:view` | Protected |
| GET | `/api/alerts/:id` | `alerts:view` | Protected |
| PATCH | `/api/alerts/:id/acknowledge` | `alerts:ack` | Protected |
| PATCH | `/api/alerts/:id/resolve` | `alerts:resolve` | Protected |
| GET | `/api/investigation/facets` | `events:view` | Protected |
| GET | `/api/investigation/suggest` | `events:view` | Protected |
| GET | `/api/investigation/journey` | `investigation:journey` | Protected |
| GET | `/api/investigation/export.csv` | `export:csv` | Protected |
| GET | `/api/correlation/sequence` | `investigation:sequence` | Protected |
| GET | `/api/topology` | `cameras:view` | Protected |
| GET | `/api/watchlist` | `watchlist:view` | Protected |
| POST | `/api/watchlist` | `watchlist:write` | Protected |
| DELETE | `/api/watchlist/:id` | `watchlist:write` | Protected |
| GET | `/api/analytics/events` | `events:view` | Protected |
| GET | `/api/analytics/cameras` | `events:view` | Protected |
| GET | `/api/analytics/threats` | `events:view` | Protected |
| GET | `/api/analytics/resolutions` | `alerts:resolve` | Protected |
| GET | `/api/snapshots/*` | `evidence:view` | Protected |
| GET | `/api/config/public` | `public` | Public |
| GET | `/api/system/status` | `system:status` | Protected |
| GET | `/api/realtime/status` | `system:status` | Protected |
| GET | `/api/ws` | `realtime:subscribe` | Protected |
| GET | `/api/users` | `users:manage` | Protected |
| POST | `/api/users` | `users:manage` | Protected |
| GET | `/api/users/:id` | `users:manage` | Protected |
| PATCH | `/api/users/:id` | `users:manage` | Protected |
| POST | `/api/users/:id/reset-password` | `users:manage` | Protected |
| POST | `/api/users/:id/disable` | `users:manage` | Protected |
| DELETE | `/api/users/:id` | `users:manage` | Protected |
| GET | `/api/notifications` | `notifications:admin` | Protected |
| GET | `/api/notifications/status` | `notifications:admin` | Protected |
| POST | `/api/notifications/test` | `notifications:admin` | Protected |
| POST | `/api/notifications/retry/:id` | `notifications:admin` | Protected |
