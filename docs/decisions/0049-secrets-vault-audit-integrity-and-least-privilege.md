# 49. Secrets Vault, Audit Integrity, and Least-Privilege Infrastructure

Date: 2026-11-13  
Status: Accepted  

## Context

Surveillance systems must protect sensitive operational secrets—such as camera RTSP credentials, cryptographic keys, and database passwords—from database breaches, unauthorized microservices, and internal administrative tampering. Furthermore, forensic evidence demands that audit logs cannot be retroactively altered, even by database administrators.

## Decisions

### 1. Camera Credential Vault (AES-256-GCM)

Camera RTSP passwords and authentication strings are encrypted using AES-256-GCM prior to persistence:
- **Nonce:** Unique 12-byte cryptographically secure random nonce per record.
- **Authenticated Additional Data (AAD):** Bound to `camera_id` (UTF-8 encoded string). This cryptographically binds the ciphertext to the specific camera entity, preventing ciphertext transplantation between rows.
- **Key Identifiers (`key_id`):** Ciphertexts include a `key_id` to enable seamless master key rotation without service downtime.
- **Cross-Language Compatibility:** The serialization format (`{ key_id, nonce, ct, tag }` with Base64 encoding) is mirrored and validated between TypeScript (Node.js `node:crypto`) and Python (`cryptography.hazmat.primitives.ciphers.aead.AESGCM`) using shared test vectors in `docs/fixtures/vault_vectors.json`.
- **Write-Only Exposure:** Camera API endpoints accept credential updates but never return credentials in plaintext or ciphertext over the REST interface.

### 2. Tamper-Evident Hash-Chained Audit Trail

All sensitive administrative and forensic actions are recorded in an append-only, cryptographically linked audit table:
- **Hash Chaining Formula:**
  $$\text{hash}_n = \text{SHA-256}(\text{hash}_{n-1} \mathbin{\Vert} \text{canonical\_json}(\text{row}_n))$$
- **Head Record:** A singleton table `audit_head` maintains the tip hash and is updated under row-level locking (`SELECT ... FOR UPDATE`) during inserts.
- **Immutability Enforcement:** A PostgreSQL trigger (`trg_prevent_audit_tampering`) aborts any attempt to execute `UPDATE` or `DELETE` on the audit log table.
- **Verification CLI:** The CLI tool `npm run audit:verify` recalculates the cryptographic chain from genesis ($0^{64}$) to the head hash, immediately identifying missing, inserted, or modified rows.

### 3. Least-Privilege Infrastructure Roles

The platform establishes distinct roles across the relational database and message broker:

#### Database Roles (PostgreSQL)
- `border_api`: Full access to API domain tables, user accounts, sessions, and `INSERT`-only access to the audit log.
- `border_engine` / `border_sink`: Read/write access restricted to detections, vehicles, and raw event queues. **Zero access** granted to `users`, `sessions`, `auth_throttle`, or `api_audit_log`.
- `border_readonly`: Read-only access to analytical views and reporting partitions.

#### Broker Permissions (Redis ACL)
- `engine`: Permissions restricted to `XADD surveillance.*`, `SET camera:status:*`.
- `sink`: Stream consumer permissions restricted to `XREADGROUP`, `XACK`, `XCLAIM` on event streams and `XADD` to dead-letter queues.
- `gateway`: Read-only stream consumer permissions on `surveillance.alerts`.
- `api`: Status reader permissions (`GET`, `MGET`, `XINFO`). Default user is explicitly disabled.

## Consequences

- Compromise of the detection engine or RTSP sink does not compromise user identities, passwords, or audit trails.
- Database dumps containing encrypted camera credentials cannot be decrypted without the master key held in environment/secret files.
- Any attempt to alter historical audit logs breaks the cryptographic hash chain and is flagged by integrity verification scanners.
