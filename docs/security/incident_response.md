# Incident Response Playbooks

This guide outlines security incident classification and operational playbooks for the Border-AI surveillance platform.

---

## 1. Severity Classification

| Severity | Definition | Target Resolution SLA | Escalation Path |
|---|---|---|---|
| **P1 - Critical** | Active intrusion, master signing key leak, vault master key exposure, audit chain tampering detected. | < 2 hours | Security Lead, Chief Architect, Infra Team |
| **P2 - High** | Account takeover, camera credential leak, denial of alert streaming, unauthorized privilege escalation. | < 6 hours | On-Call Security Engineer, Backend Lead |
| **P3 - Medium** | Brute force alert triggered, unauthorized CORS preflight spike, non-critical endpoint 500 error. | < 24 hours | On-Call Engineer |
| **P4 - Low** | Dependency vulnerability without active exploit path, minor configuration drift. | Next sprint | Development Team |

---

## 2. Playbook 1: Access Token Compromise / Account Takeover

### Triggers:
- Stolen bearer token detected in unauthorized location or unusual IP.
- Concurrent logins from geographically impossible locations.

### Immediate Action (T < 15m):
1. **Revoke Active User Sessions:**
   Run CLI revocation or execute administrative API endpoint:
   ```bash
   # Invalidate all active sessions for the compromised user
   curl -X POST http://localhost:4000/api/users/:userId/revoke-sessions \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```
2. **Bump User Token Version:**
   In Postgres:
   ```sql
   UPDATE users SET token_version = token_version + 1, updated_at = now() WHERE id = 'compromised-user-id';
   ```
   All existing JWTs for this user immediately fail verification (`TOKEN_VERSION_REVOKED`).
3. **Reset User Password:**
   Generate temporary compliant password and force password change flag.
4. **Audit Review:**
   Inspect `api_audit_log` for actions performed by the compromised actor during the window:
   ```sql
   SELECT at, action, entity_type, entity_id, ip, detail
   FROM api_audit_log
   WHERE actor = 'compromised-user-id'
   ORDER BY at DESC;
   ```

---

## 3. Playbook 2: Master Signing Key or Vault Key Compromise

### Triggers:
- Accidental commit of `ed25519-private.pem` or `VAULT_MASTER_KEY` to public repository.
- Host machine memory dump compromise.

### Immediate Action (T < 30m):
1. **Generate New Ed25519 Keypair:**
   ```bash
   npm --prefix backend run keys:generate
   ```
2. **Deploy Dual-Key JWKS Rotation:**
   - Keep old public key in JWKS for 15 minutes grace period.
   - Point active signing key to the new key ID (`kid`).
   - After grace period, remove compromised public key completely.
3. **Re-seal Camera Credentials:**
   Run the vault re-encryption script with the new `VAULT_MASTER_KEY`:
   ```bash
   # Re-encrypt camera credentials table with new key ID
   npm --prefix backend run vault:re-seal -- --old-key $OLD_KEY --new-key $NEW_KEY
   ```
4. **Restart API and Python Engine Workers:**
   Force reloading of environment secrets.

---

## 4. Playbook 3: Rogue Camera Ingest / Stream Spoofing

### Triggers:
- Video stream content mismatch or anomalous network source traffic to MediaMTX / Engine.
- Engine reports invalid stream signature or expired stream token.

### Immediate Action (T < 15m):
1. **Isolate Camera in System:**
   Set camera status to `OFFLINE` or `MAINTENANCE` via API:
   ```bash
   curl -X PATCH http://localhost:4000/api/cameras/cam-compromised \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"status": "MAINTENANCE"}'
   ```
2. **Invalidate Stream Tokens:**
   Rotate engine stream token verification public key. Engine will immediately drop any active RTSP/MJPEG consumers without valid signatures.
3. **Verify Network Isolation:**
   Check RTSP stream VLAN ingress ACL to block unauthorized camera IP.

---

## 5. Playbook 4: Audit Log Hash Chain Tampering

### Triggers:
- `npm run audit:verify` exits with code 1 indicating `[AUDIT INTEGRITY BREACH]`.

### Immediate Action (T < 30m):
1. **Identify Broken Link:**
   Note the sequence number and recorded hash reported by `npm run audit:verify`.
2. **Isolate Database Access:**
   Revoke `border_api` and any external DB connection pool immediately to preserve forensic evidence:
   ```sql
   ALTER USER border_api NOLOGIN;
   ```
3. **Inspect PostgreSQL WAL and Replication Logs:**
   Compare the current table state against transaction log backups (Point-in-Time Recovery) to determine exact time and user who issued modifications.
4. **Preserve Forensic Dump:**
   Export intact chain prefix up to `brokenAt` and isolate tampered record.
