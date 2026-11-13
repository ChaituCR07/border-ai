# 48. Authorization: Permission Policy, Role Mappings, and Deny-by-Default Architecture

Date: 2026-11-13  
Status: Accepted  

## Context

Prior versions of the Border-AI API relied on scattered role checks (e.g., `requireRole('ADMIN')`) attached to specific route handlers. In a mission-critical border surveillance system, an unmapped or forgotten route represents an immediate security exposure. Furthermore, roles like "Investigator" require read-only access to operational rules and thresholds to evaluate alerts without the risk of accidentally or maliciously altering detection logic.

## Decisions

### 1. Unified Permission Model

The platform replaces hardcoded role checks with fine-grained granular permissions. Route handlers specify a required permission; handlers never query role names directly.

| Role | Operational Scope | Live View | Alerts | Watchlist | Evidence (Persons) | Configuration |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **VIEWER** | Real-time monitoring & situational awareness | ✓ | View Only | ✗ | Redacted Placeholder | ✗ |
| **OPERATOR** | Incident response & acknowledgment | ✓ | Ack & Resolve | ✗ | Full Evidence | ✗ |
| **INVESTIGATOR** | Forensic search, vehicle journey & watchlist audit | ✓ | Ack & Resolve | ✓ | Full Evidence | **Limited (Read-Only)** |
| **ADMIN** | System management, users, and policy changes | ✓ | Ack & Resolve | ✓ | Full Evidence | Full Write |

### 2. Permissions Definition

```text
live:view                 -> Stream access and stream token minting
alerts:view               -> Read alerts, statistics, and alert facets
alerts:ack                -> Acknowledge pending alerts
alerts:resolve            -> Mark alerts resolved with operational outcome
events:view               -> Search events, timeline facets, and analytics
evidence:view             -> Access raw snapshot images and facial crops
investigation:journey     -> Multi-camera cross-corridor vehicle tracking
investigation:person_search -> Attribute-based person search (requires purpose)
investigation:sequence    -> Temporal-spatial trajectory correlation (requires purpose)
export:csv                -> Export investigation telemetry (requires purpose)
watchlist:view            -> Read target license plates and descriptions
watchlist:write           -> Add, update, or remove watchlist entries
config:read               -> View system thresholds, rules, and alert topologies
config:write              -> Modify operational thresholds and notification routes
cameras:view              -> View camera hardware registry and status
cameras:write             -> Register, update, or decommission cameras
topology:write            -> Update camera spatial adjacency graph
notifications:admin       -> Configure webhook/SMTP routes and trigger test emails
users:manage              -> Create users, modify roles, reset passwords, disable accounts
audit:view                -> Query and verify tamper-evident audit logs
retention:run             -> Execute data retention pruning tasks
system:status             -> View high-level system telemetry
system:detail             -> View internal queues, Redis memory, and diagnostic metrics
realtime:subscribe        -> Open WebSocket event stream (issue tickets)
```

### 3. Deny-by-Default Route Enforcement
- **Fastify `onRoute` Hook:** During server startup, every registered route is inspected. If a route does not explicitly define either a valid `config.permission` or `config.public = true`, the server throws an exception and halts initialization.
- **Global `preHandler` Guard:** For non-public routes, the global pre-handler validates the access token, verifies the user status and token version, checks `ROLE_PERMISSIONS[role].has(permission)`, and denies unauthorized requests with `403 FORBIDDEN`.

### 4. Special Protective Constraints
- **Last Active Admin Protection:** The API prevents deleting, disabling, or demoting an administrator if they are the sole active `ADMIN` in the system.
- **Person Evidence Privacy Redaction:** When users holding only `VIEWER` role request evidence snapshots containing person detections, the endpoint returns an SVG/PNG redacted placeholder image rather than an error or the raw image.
- **Mandatory Justification for Forensic Queries:** Endpoints tagged with privacy sensitivity (`investigation:person_search`, `investigation:sequence`, `export:csv`) require a non-empty `purpose` parameter, which is recorded in the immutable audit log.

## Consequences

- No route can accidentally be exposed without an explicit access policy.
- Automated tests verify that every registered route conforms to the RBAC matrix.
- Investigator role is strictly bounded to read-only oversight for configuration files.
