# Border-AI Backend REST API

High-performance, typed backend REST API service built with Node.js 22/24 LTS, TypeScript, Fastify v5, Zod, and PostgreSQL. Exposes cameras, video analytics events, threat alerts, non-biometric watchlist management, and operational analytics for the Border-AI Command Dashboard.

---

## 1. Quick Start

### Prerequisites
- Node.js >= 22 LTS
- Docker and Docker Compose (PostgreSQL 16 & Redis 7)

### Environment Configuration
```bash
cp .env.example .env
```

Key environment variables:
| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `4000` | HTTP service port |
| `HOST` | `0.0.0.0` | Listen host |
| `DATABASE_URL` | `postgres://border_api:border_api_secret@localhost:5432/borderai` | Main database |
| `TEST_DATABASE_URL` | `postgres://border_api:border_api_secret@localhost:5432/borderai_test` | Test database |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |
| `SNAPSHOT_DIR` | `../outputs/runs` | Path to evidence snapshots |
| `MJPEG_BASE_URL` | `http://localhost:8001` | Live stream gateway |

---

## 2. Scripts Reference

```bash
# Start development server with file watch and tsx
npm run dev

# Run static type checking
npm run typecheck

# Build production bundle
npm run build

# Start production bundle
npm start

# Run all unit, contract, and route tests (in-memory)
npm test

# Run real PostgreSQL integration and cross-language e2e tests
npm run test:db

# Seed synthetic surveillance events for pagination and stress testing
npm run seed -- --events 5000 --cameras 6 --days 7

# Run automated smoke test suite
npm run smoke
```

---

## 3. Architecture Overview

- **Framework:** Fastify v5 with schema-first Zod validation (`fastify-type-provider-zod`).
- **Data Access:** Handwritten SQL via `pg` (node-postgres) with custom type parsers preserving microsecond precision for `timestamptz`.
- **Repository Pattern:** Dual-backend parity across all domain modules:
  - `repo.memory.ts` for instant, isolated unit and route testing.
  - `repo.pg.ts` for production database operations with parameterized queries.
- **Keyset Pagination:** Stable $O(1)$ cursor pagination on `(timestamp DESC, event_id DESC)` avoiding `OFFSET` drift.
- **Idempotent State Machines:** Safe multi-operator alert acknowledgement without race conditions.
- **OpenAPI / Swagger:** Interactive documentation available at `http://localhost:4000/docs`.

---

## 4. Testing Matrix

1. **Unit Tests (`tests/unit/`):** Pure function tests for time parsing, base64url pagination cursors, plate normalization fixtures, and error classes.
2. **Contract Tests (`tests/contract/`):** Parity suites verifying that `InMemory` and `Pg` repositories adhere to the identical contract.
3. **Route Tests (`tests/routes/`):** Fastify injection tests verifying all 15 endpoints, query validation, and path traversal security.
4. **Integration Tests (`tests/integration/`):** Real PostgreSQL queries, keyset cursor pagination with microsecond comparisons, and 10-worker concurrent acknowledge tests.
5. **Cross-Language E2E Tests (`tests/e2e/`):** Python `PostgresEventSink` -> PostgreSQL -> Fastify REST API query verification.
