# Database Subsystem (`database`)

The **Database** module manages schema definitions, data migrations, and seed records for the platform's primary relational database running on PostgreSQL 16.

---

## 1. Directory Structure

```text
database/
├── schema.sql                 # Base database schema definition (Week 2)
├── migrations/                # Version-controlled schema migrations
└── seeds/                     # Initial seed data (sample watchlists, cameras)
```

---

## 2. Core Entities (Planned Schema for Week 2)

| Table | Responsibility |
|---|---|
| `cameras` | Registered camera streams, display names, RTSP URLs, and status |
| `events` | Detected security incidents, zone breaches, timestamps, and threat scores (0–100) |
| `watchlist` | Flagged vehicle license plates, stolen car alerts, and watchlist categories |
| `snapshots` | Metadata linking cropped detection images to specific event records |
| `audit_logs` | Security operator activity, alert acknowledgments, and incident resolutions |

---

## 3. Database Access & Management

PostgreSQL runs containerized via Docker on port `5432`:

### Direct CLI Access (via Docker)
```bash
docker exec -it borderai-postgres psql -U borderai -d borderai
```

### Connectivity Verification
```bash
docker exec borderai-postgres psql -U borderai -d borderai -c "SELECT 1;"
```

### Environment Configuration
Database credentials and endpoints are defined in `.env`:
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=borderai
POSTGRES_USER=borderai
POSTGRES_PASSWORD=your_password
```
