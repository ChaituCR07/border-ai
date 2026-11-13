# Secrets Management & Vault Lifecycle

This document defines secrets handling, provisioning conventions, and key rotation procedures for Border-AI.

---

## 1. Secrets Inventory

| Secret Name | Purpose | Format | Storage Location |
|---|---|---|---|
| `JWT_PRIVATE_KEY` / `JWT_PRIVATE_KEY_PATH` | EdDSA JWT token signing | PKCS#8 PEM Ed25519 | Env var or Docker Secret file |
| `JWT_PUBLIC_KEY` / `JWT_PUBLIC_KEY_PATH` | EdDSA token verification | SubjectPublicKeyInfo PEM | Env var or Docker Secret file |
| `VAULT_MASTER_KEY` | AES-256-GCM camera credential vault | 32 bytes (hex or base64) | Secure Env or Key Vault |
| `DATABASE_URL` | PostgreSQL connection string | URI with password | Env var or Docker Secret file |
| `REDIS_URL` | Redis ACL connection string | URI with auth token | Env var or Docker Secret file |

---

## 2. Docker & Kubernetes Secrets Conventions

Border-AI supports the twelve-factor application convention alongside file-based secrets injection (`*_FILE` pattern) to prevent exposing credentials via process listings (`ps aux`):

```bash
# If set, the application reads the secret from the mounted path:
export JWT_PRIVATE_KEY_PATH="/run/secrets/jwt_private_key"
export VAULT_MASTER_KEY_PATH="/run/secrets/vault_master_key"
```

---

## 3. Cryptographic Key Rotation Procedures

### 3.1 Ed25519 Access Token Signing Key Rotation
1. **Generate New Keypair:**
   ```bash
   npm --prefix backend run keys:generate
   ```
2. **Add New Public Key to JWKS:**
   Register the new key in the JWKS store with a distinct `kid` (e.g. `border-ai-ed25519-2026-q4`).
3. **Switch Active Signing Key:**
   Update `JWT_ACTIVE_KID` to the new key ID. All newly issued access tokens will use the new key.
4. **Grace Period (15 Minutes):**
   Existing tokens signed by the previous key remain verifiable through JWKS until their expiration (max 15m).
5. **Retire Old Key:**
   Remove the old key from JWKS after expiration.

### 3.2 AES-256-GCM Camera Credential Vault Key Rotation
Each camera credential envelope contains a `key_id` tag:
```json
{
  "key_id": "vault-2026-v1",
  "nonce": "...",
  "ct": "...",
  "tag": "..."
}
```
During key rotation:
1. Maintain both `VAULT_MASTER_KEY` (active) and `VAULT_PREVIOUS_KEYS` (map of `key_id -> key`).
2. Run database migration script to decrypt credentials with the old key and re-encrypt with the new active key ID.
3. Purge the retired key once all camera rows report the latest `key_id`.
