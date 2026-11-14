# Version Upgrade and Rollback Runbook

This document details the operational process for upgrading Border-AI between platform releases (e.g. `v1.0.0` to `v1.1.0`), running database schema migrations, and executing emergency rollbacks.

---

## 1. Upgrade Lifecycle Principles

1. **Immutable Images:** Container images are pinned by exact version tag or SHA-256 digest. In-place patching inside containers is prohibited.
2. **Backward-Compatible Schema:** Database migrations (`backend/prisma` or SQL migrations) must follow the expand-contract pattern to support zero-downtime rolling deploys.
3. **Automated Pre-Flight Backup:** An encrypted backup is automatically executed prior to any schema application.

---

## 2. Standard Upgrade Workflow

To upgrade a production installation:

```bash
# 1. Fetch updated repository code / tags
git fetch --tags
git checkout v1.1.0

# 2. Take immediate pre-upgrade snapshot backup
make backup

# 3. Pull new base images and rebuild application containers
docker compose pull
docker compose build

# 4. Execute database schema migration container
docker compose run --rm migrate

# 5. Restart services with rolling replacement
docker compose up -d --remove-orphans

# 6. Verify stack health and edge routing
make smoke-compose
```

---

## 3. Database Migration Idempotency

All schema migrations in `backend/prisma/migrations/` or custom migration runners must be strictly idempotent:
- Use `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, etc.
- Safe to re-run multiple times without failure or data corruption.
- Migration runner tracks applied versions in the `_prisma_migrations` table.

---

## 4. Emergency Rollback Procedure

If critical regressions are encountered after upgrading:

1. **Revert Application Images:**
   ```bash
   git checkout <previous_stable_tag>
   docker compose build
   ```

2. **Restore Pre-Upgrade Database (if schema was incompatible):**
   ```bash
   PRE_UPGRADE_BACKUP=$(ls -t backups/*_postgres.sql.enc | head -n 1)
   PRE_UPGRADE_SNAPS=$(ls -t backups/*_snapshots.tar.gz.enc | head -n 1)
   scripts/restore.sh "$PRE_UPGRADE_BACKUP" "$PRE_UPGRADE_SNAPS"
   ```

3. **Restart Platform:**
   ```bash
   docker compose up -d --force-recreate
   make smoke-compose
   ```
