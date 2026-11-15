# Border-AI API Permissions & Role-Based Access Control (RBAC) Matrix

This document maps all REST API endpoints and WebSocket channels to the required permissions and authorized user roles (`VIEWER`, `OPERATOR`, `INVESTIGATOR`, `ADMIN`), as defined in `backend/src/security/policy.ts` (ADR 0048).

---

## 1. Role Definitions & Privilege Tiers

- **`VIEWER`:** Read-only surveillance monitoring. Can view live video streams, active alerts, and camera status. Cannot acknowledge alerts, search forensic journey histories, or view evidence snapshots.
- **`OPERATOR`:** Active perimeter guard. Can view live feeds, triage/acknowledge incoming alerts, resolve incidents, and view immediate evidence snapshots.
- **`INVESTIGATOR`:** Forensic analysis persona. Full access to cross-camera journey reconstruction, vehicle plate search, look-alike queries, sequence search, CSV data exports, and watchlist management. Cannot modify system config or manage user accounts.
- **`ADMIN`:** Full platform control. Manages camera registrations, spatial topologies, notification outbox, user provisioning, role assignments, system status details, and manually triggered retention purges.

---

## 2. API Endpoint to Permission Matrix

| HTTP Method | API Path | Endpoint Operation | Required Permission | Viewer | Operator | Investigator | Admin |
|---|---|---|---|:---:|:---:|:---:|:---:|
| `POST` | `/api/v1/auth/login` | User Authentication | *Public* | &#10004; | &#10004; | &#10004; | &#10004; |
| `POST` | `/api/v1/auth/refresh` | Refresh Access Token | *Public* | &#10004; | &#10004; | &#10004; | &#10004; |
| `POST` | `/api/v1/auth/logout` | Revoke Session | *Authenticated* | &#10004; | &#10004; | &#10004; | &#10004; |
| `GET` | `/api/v1/cameras` | List All Cameras | `cameras:view` | &#10004; | &#10004; | &#10004; | &#10004; |
| `POST` | `/api/v1/cameras` | Register New Camera | `cameras:write` | &#10006; | &#10006; | &#10006; | &#10004; |
| `PUT` | `/api/v1/cameras/:id` | Update Camera Stream | `cameras:write` | &#10006; | &#10006; | &#10006; | &#10004; |
| `GET` | `/api/v1/streams/:id/mjpeg`| Live MJPEG Video Stream | `live:view` | &#10004; | &#10004; | &#10004; | &#10004; |
| `GET` | `/api/v1/events` | Keyset Paginated Events | `events:view` | &#10004; | &#10004; | &#10004; | &#10004; |
| `GET` | `/api/v1/alerts` | List Open/Resolved Alerts | `alerts:view` | &#10004; | &#10004; | &#10004; | &#10004; |
| `PATCH`| `/api/v1/alerts/:id/ack` | Acknowledge Alert | `alerts:ack` | &#10006; | &#10004; | &#10004; | &#10004; |
| `PATCH`| `/api/v1/alerts/:id/res` | Resolve Alert | `alerts:resolve` | &#10006; | &#10004; | &#10004; | &#10004; |
| `GET` | `/api/v1/snapshots/:id` | Forensic Evidence Image | `evidence:view` | &#10006; | &#10004; | &#10004; | &#10004; |
| `GET` | `/api/v1/investigation/journey` | Vehicle Journey Search | `investigation:journey` | &#10006; | &#10004; | &#10004; | &#10004; |
| `POST` | `/api/v1/investigation/sequence` | Multi-Camera Sequence Search | `investigation:sequence` | &#10006; | &#10006; | &#10004; | &#10004; |
| `GET` | `/api/v1/export/csv` | Forensic CSV Data Export | `export:csv` | &#10006; | &#10006; | &#10004; | &#10004; |
| `GET` | `/api/v1/watchlist` | List Watchlist Entries | `watchlist:view` | &#10006; | &#10006; | &#10004; | &#10004; |
| `POST` | `/api/v1/watchlist` | Add Plate to Watchlist | `watchlist:write` | &#10006; | &#10006; | &#10004; | &#10004; |
| `GET` | `/api/v1/config` | Read System Config | `config:read` | &#10006; | &#10006; | &#10004; | &#10004; |
| `PUT` | `/api/v1/config` | Modify System Config | `config:write` | &#10006; | &#10006; | &#10006; | &#10004; |
| `GET` | `/api/v1/topology` | Inter-Camera Topology | `cameras:view` | &#10004; | &#10004; | &#10004; | &#10004; |
| `PUT` | `/api/v1/topology` | Update Transition Bounds | `topology:write` | &#10006; | &#10006; | &#10006; | &#10004; |
| `GET` | `/api/v1/users` | List User Accounts | `users:manage` | &#10006; | &#10006; | &#10006; | &#10004; |
| `POST` | `/api/v1/users` | Create User Account | `users:manage` | &#10006; | &#10006; | &#10006; | &#10004; |
| `GET` | `/api/v1/audit/logs` | Immutable Audit Trail | `audit:view` | &#10006; | &#10006; | &#10006; | &#10004; |
| `POST` | `/api/v1/retention/run` | Execute Data Purge | `retention:run` | &#10006; | &#10006; | &#10006; | &#10004; |
| `GET` | `/api/v1/system/status` | Component Health Check | `system:status` | &#10004; | &#10004; | &#10004; | &#10004; |
| `GET` | `/api/v1/system/detail` | Detailed Engine Metrics | `system:detail` | &#10006; | &#10006; | &#10006; | &#10004; |
| `WS` | `/api/v1/ws` | Real-Time Alert Gateway | `realtime:subscribe` | &#10004; | &#10004; | &#10004; | &#10004; |
