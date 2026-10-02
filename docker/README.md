# Docker & Container Infrastructure (`docker`)

The `docker/` directory contains configuration files, initialization scripts, and network proxies used to orchestrate containerized services across the Border AI platform.

---

## 1. Directory Structure

```text
docker/
├── postgres/
│   └── init.sql               # PostgreSQL container initialization script
└── nginx/                     # Reverse proxy & gateway configurations (Weeks 3-4)
```

Root orchestration file:
- `docker-compose.yml`: Defines container services, ports, volume bindings, and healthcheck policies.

---

## 2. Running Services

### 1. PostgreSQL 16 (`borderai-postgres`)
- **Port:** `5432`
- **Volume:** `pgdata` (persisted to `/var/lib/postgresql/data`)
- **Healthcheck:** Evaluates `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` every 5 seconds.
- **Initialization:** Automatically mounts `docker/postgres/init.sql` to `/docker-entrypoint-initdb.d/init.sql`.

### 2. Redis 7 (`borderai-redis`)
- **Port:** `6379`
- **Volume:** `redisdata` (persisted to `/data`)
- **Command:** `redis-server --appendonly yes` (AOF persistence enabled)
- **Healthcheck:** Evaluates `redis-cli ping` every 5 seconds.

---

## 3. Container Management Commands

### Start All Infrastructure
```bash
docker compose up -d
```
Or via Makefile:
```bash
make up
```

### Inspect Container Health & Status
```bash
docker compose ps
```
Both containers will display `(healthy)`.

### Stop Containers (Preserving Database Data)
```bash
docker compose down
# or: make down
```

### Full Factory Reset (Purging All Database Volumes)
```bash
docker compose down -v
```
