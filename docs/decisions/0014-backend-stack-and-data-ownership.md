# ADR 0014 — Backend Stack, Framework Choice, and Data Ownership

## Status
Accepted

## Context
Week 3 transitions the Border-AI Video Intelligence Platform into productization, dashboards, and live operator control. The backend REST API must bridge the PostgreSQL data layer created in Day 14 to operator dashboards (Day 16), live WebSocket alerts (Day 17), and forensic investigation workflows (Day 18).

The architecture requires strict boundaries between the Python AI engine (which processes video ingestion, YOLO, ByteTrack, ANPR, face recognition, behavior rules, and threat scoring) and the Node.js REST API service.

## Decision
1. **Technology Stack:**
   - **Runtime:** Node.js 22/24 LTS with TypeScript (strict mode, NodeNext module resolution).
   - **HTTP Framework:** Fastify v5 with `fastify-type-provider-zod` and Zod schema-first compilation.
   - **Database Client:** `pg` (node-postgres) with parameterized handwritten SQL. No ORM is used to ensure SQL transparency, optimal query performance, and shared migration ownership with Python.
   - **Security & Reliability:** `@fastify/helmet`, `@fastify/cors`, `@fastify/rate-limit`, and OpenAPI auto-generation via `@fastify/swagger` and `@fastify/swagger-ui`.

2. **Strict Data Ownership Model:**
   To prevent dual-writer race conditions and maintain database integrity:
   - `events`, `detections`, `vehicles`: **Written exclusively by Python** (`PostgresEventSink`). Node API has read-only access.
   - `alerts`: Created initially by Python (`PostgresEventSink`). Node API manages lifecycle status transitions only (e.g. `PATCH /alerts/:id/acknowledge`).
   - `cameras`: Python auto-registers cameras on first event; Node API manages full administrative CRUD.
   - `watchlist`: Read by Python for real-time plate and biometric matching; Node API manages administrative CRUD for non-biometric fields.
   - `api_audit_log`: Written exclusively by Node API to maintain immutable audit records of operator actions.

3. **Least-Privilege Database Role:**
   The API connects using a dedicated `border_api` database role with restricted permissions matching the ownership table above.

## Consequences
- **Positive:**
  - Fastify offers lower overhead and higher throughput than Express, built-in structured Pino logging, and seamless integration with `@fastify/websocket` for Day 17.
  - Zero dual-writer race conditions on core surveillance events.
  - Handwritten SQL ensures exact alignment with indexes and query execution plans.
- **Negative:**
  - Requires maintaining repository abstractions for both in-memory testing and PostgreSQL execution.
