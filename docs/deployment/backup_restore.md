# Disaster Recovery: Backup and Restore Runbook

This runbook documents the procedures for automated encrypted backups, integrity verification, snapshot restoration, and point-in-time disaster recovery for Border-AI.

---

## 1. Backup Strategy Overview

Border-AI implements an automated, encrypted disaster recovery procedure (`scripts/backup.sh` and `scripts/restore.sh`):

- **Database Engine State:** Consistent SQL dump via `pg_dump` with transaction isolation.
- **Forensic Snapshots:** Compressed archive of `/var/lib/border-ai/snapshots/`.
- **Encryption:** AES-256-CBC with PBKDF2 key derivation using the vault master key (`secrets/vault_master_key`).
- **Integrity Verification:** Cryptographic SHA-256 checksum generated per archive and stored alongside the backup.
- **Secrets Exclusion:** Master secrets and private keys are **never** included in backups; they are managed under separate key management runbooks.

---

## 2. Automated Backup Execution

Backups can be triggered manually or via cron:

```bash
# Execute automated backup to default directory (backups/)
make backup

# Or specify custom destination directory
BACKUP_DIR=/mnt/secure_nfs/border_backups scripts/backup.sh
```

### Backup Output Structure
```
backups/
├── backup_20261114_230000_postgres.sql.enc
├── backup_20261114_230000_postgres.sql.enc.sha256
├── backup_20261114_230000_snapshots.tar.gz.enc
└── backup_20261114_230000_snapshots.tar.gz.enc.sha256
```

---

## 3. Disaster Recovery Restoration Procedure

To restore a platform instance from an encrypted backup archive:

```bash
# Full restore using restore script
scripts/restore.sh backups/backup_20261114_230000_postgres.sql.enc backups/backup_20261114_230000_snapshots.tar.gz.enc
```

### Step-by-Step Restoration Phases
1. **Integrity Validation:** Verifies SHA-256 checksums match `*.sha256` files.
2. **Decryption:** Decrypts archives using `secrets/vault_master_key` into temporary secure memory.
3. **Database Population:** Restores database tables, constraints, sequences, and indexes.
4. **Snapshot Restoration:** Restores forensic imagery to `/var/lib/border-ai/snapshots/` with non-root ownership.
5. **Reconciliation:** Executes reconciliation check to confirm entity counts match forensic logs.

---

## 4. Disaster Recovery Drill Verification Checklist

| Verification Check | Target Outcome | Status |
|---|---|---|
| PostgreSQL row count check | Post-restore counts for `events`, `alerts`, `users` match pre-backup counts | Verified |
| Snapshot file availability | Random sample of 100 snapshot URLs return HTTP 200 through proxy | Verified |
| Healthcheck status | All services report `(healthy)` within 30 seconds of restore | Verified |
| Smoke test execution | `make smoke-compose` passes cleanly post-restore | Verified |
