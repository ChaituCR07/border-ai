# Secrets Rotation Runbook

This runbook outlines the standard operating procedure for rotating authentication credentials, database passwords, TLS certificates, and cryptographic keys without data loss.

---

## 1. Secrets Inventory & Risk Profile

| Secret Identifier | Rotation Frequency | Impact of Rotation | Downtime Required |
|---|---|---|---|
| `jwt_private_key` & `jwt_public_key` | 90 days | Invalidation of active user sessions | Zero (using dual-key transition) |
| `postgres_admin_password` | 180 days | Maintenance operations only | Zero |
| `backend_db_password` | 90 days | Temporary DB reconnect | Sub-second |
| `redis_backend_password` | 90 days | Temporary Redis reconnect | Sub-second |
| `vault_master_key` | 365 days | Requires re-encryption of snapshot archive metadata | Maintenance window |
| `edge.crt` & `edge.key` (TLS) | 90–365 days | Browser TLS handshake renegotiation | Zero (graceful Nginx reload) |

---

## 2. Zero-Downtime TLS Certificate Rotation

When updating or renewing edge TLS certificates:

```bash
# 1. Place the new certificate and private key into certs/
cp /path/to/new_cert.crt certs/edge.crt
cp /path/to/new_key.key certs/edge.key
chmod 644 certs/edge.crt
chmod 600 certs/edge.key

# 2. Test the Nginx configuration syntax inside the live container
docker compose exec nginx nginx -t

# 3. Gracefully reload Nginx workers without dropping connections
docker compose exec nginx nginx -s reload
```

---

## 3. Database Password Rotation Procedure

To rotate database user credentials (e.g. `border_backend`):

1. **Generate New Secret:**
   ```bash
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))" > secrets/backend_db_password.new
   ```

2. **Update Password in PostgreSQL:**
   ```bash
   NEW_PW=$(cat secrets/backend_db_password.new)
   docker compose exec postgres psql -U postgres -d border_ai -c "ALTER ROLE border_backend WITH PASSWORD '$NEW_PW';"
   ```

3. **Promote New Secret:**
   ```bash
   mv secrets/backend_db_password.new secrets/backend_db_password
   chmod 600 secrets/backend_db_password
   ```

4. **Restart Dependent Services:**
   ```bash
   docker compose restart backend
   ```

---

## 4. Ed25519 JWT Key Rotation

1. **Generate New Keypair:**
   ```bash
   node -e "
   const { generateKeyPairSync } = require('crypto');
   const { privateKey, publicKey } = generateKeyPairSync('ed25519', {
     publicKeyEncoding: { type: 'spki', format: 'pem' },
     privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
   });
   require('fs').writeFileSync('secrets/jwt_private_key.new', privateKey);
   require('fs').writeFileSync('secrets/jwt_public_key.new', publicKey);
   "
   ```

2. **Atomic Swap & Reload:**
   ```bash
   mv secrets/jwt_private_key.new secrets/jwt_private_key
   mv secrets/jwt_public_key.new secrets/jwt_public_key
   chmod 600 secrets/jwt_private_key
   chmod 644 secrets/jwt_public_key

   docker compose restart backend
   ```
   *Note: Active client JWTs will trigger refresh token exchange against the new verification key.*

---

## 5. Emergency Revocation (Credential Breach)

If a credential leak is detected:
1. Immediately run `scripts/gen_secrets.sh --force` into a staging folder.
2. Terminate all active sessions via Redis flush: `docker compose exec redis redis-cli -a <password> FLUSHDB`.
3. Re-run `docker compose up -d --force-recreate` to mount fresh credentials stack-wide.
4. Review audit logs via `GET /api/v1/audit/logs` to identify compromised operations.
