# PostgreSQL Role & Grant Architecture

In Border-AI, database roles and least-privilege permissions are **NOT** provisioned by unverified static scripts inside `/docker-entrypoint-initdb.d/`.

Instead, they are managed deterministically by the idempotent `db-init` container job (`dist/scripts/db-init.js`), which reads individual credentials from Docker Compose secrets (`/run/secrets/*`):

| Role | Password Secret | Permissions Summary |
|---|---|---|
| `postgres` (Superuser) | `pg_admin_password` | Database owner, runs schema migrations (`migrate` job). |
| `border_api` | `pg_api_password` | Read/write to users, sessions, cameras, watchlist; read-only to events. |
| `border_engine` | `pg_engine_password` | Read-only to cameras, config; **NO access to `users` or `sessions`**. |
| `border_sink` | `pg_sink_password` | INSERT-only to events, detections, alerts; **NO access to `users` or `sessions`**. |
| `border_retention` | `pg_retention_password` | DELETE-only for expired event/snapshot tables + INSERT to audit log. |
| `border_readonly` | Auto-generated | Read-only reporting queries. |
