# Border-AI Administrator & Systems Operations Guide

This guide details configuration, user provisioning, security policies, and maintenance tasks for system administrators.

---

## 1. User Account Provisioning & RBAC Management

Administrators manage system access via the **Administration** view (`/admin/users`) or the REST API:
- **Roles:** Assign users to `VIEWER`, `OPERATOR`, `INVESTIGATOR`, or `ADMIN`.
- **Password Security:** Passwords are automatically hashed using Argon2id with random salts.
- **Revoking Access:** Deactivating a user immediately invalidates all active session tokens and terminates ongoing WebSocket streams.

---

## 2. Camera & Spatial Analytics Configuration

To configure camera feeds and spatial tripwires:
1. Navigate to **`Settings -> Cameras`**.
2. Click **`Add Camera`** and provide:
   - Camera Identifier (e.g. `CAM-005-GATE`)
   - RTSP Stream URL (`rtsp://user:pass@camera-ip:554/stream1`)
   - Ingestion FPS target (Default: 15 FPS)
3. **Drawing Polygonal Zones:**
   - Select the camera viewport and choose **`Add Zone`**.
   - Click to define polygon vertices covering the restricted area.
   - Designate zone type: `restricted` (triggers intrusion rules), `buffer` (triggers warning score), or `transit`.
4. **Drawing Virtual Tripwires:**
   - Click two points to define a virtual line.
   - Choose crossing directionality: `ingress`, `egress`, or `bidirectional`.

---

## 3. Maintenance, Backup & Retention Policies

### Automated Backups
```bash
# Execute full encrypted database & snapshot backup
make backup
```
Encrypted archives (`*.sql.enc`, `*.tar.gz.enc`) and SHA-256 checksums are stored in `backups/`.

### Automated Data Retention
The platform's background retention worker executes daily according to `.env` policies:
- `RETENTION_EVENTS_DAYS=90`: Deletes event rows older than 90 days.
- `RETENTION_ALERTS_DAYS=180`: Purges resolved alerts and deletes snapshot files from `/var/lib/border-ai/snapshots/`.
- `RETENTION_AUDIT_DAYS=365`: Retains immutable compliance audit logs.

### Audit Log Cryptographic Verification
Verify the SHA-256 tamper-proof hash chain of the administrative audit log:
```bash
npm --prefix backend run audit:verify
```
