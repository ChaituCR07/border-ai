# ADR 0052: Secrets Provisioning, Edge Proxy, TLS, and Operations

## Status
Accepted

## Context
Deploying video intelligence platforms requires robust management of confidential cryptographic credentials (signing keys, database passwords, encryption vault keys), secure client communications, and operational resiliency (graceful shutdown, data retention, backup/recovery).

## Decision

1. **File-Based Secrets Provisioning (`*_FILE` Pattern):**
   - No passwords, private keys, or API tokens may be passed via environment variables in `docker-compose.yml` or baked into images.
   - All credentials are generated into a protected host directory (`secrets/` with permissions `0750`/`0440`), mounted as Docker Compose secrets at `/run/secrets/*`.
   - Services load secrets directly from file paths specified by `*_FILE` environment variables (conforming to Day 26 ADR 0049).
   - Redis enforces an Access Control List (ACL) file containing SHA-256 hashed credentials rather than plaintext passwords.

2. **Hardened Nginx Edge Proxy:**
   - Enforces TLS 1.3 / TLS 1.2 with strong modern cipher suites and Strict-Transport-Security (HSTS).
   - Activates HTTP/2 (`http2 on`) to eliminate the browser 6-connection-per-host limitation during concurrent MJPEG video streaming.
   - Overwrites `X-Forwarded-For` with the remote client IP to prevent IP spoofing; Fastify backend trusts only the internal Nginx subnet.
   - Disables proxy buffering (`proxy_buffering off`) and response caching on `/stream/` to ensure real-time MJPEG packet delivery.
   - Handles WebSocket upgrades on `/api/ws` with extended read/write timeouts (3600s) matching the platform's 15s heartbeat architecture.
   - Omits query strings from Nginx access logs (`$uri` instead of `$request_uri`) to prevent logging WebSocket tickets or stream authorization tokens.

3. **Operational Discipline:**
   - **Graceful Shutdown:** Engine and backend intercept `SIGTERM` with extended stop grace periods (30s–45s) to flush RAM publisher buffers and WAL journals before process exit.
   - **Data Retention Service:** Automated background retention service purges events, snapshots, and audit entries exceeding retention windows, writing cryptographic audit log entries for each batch.
   - **Encrypted Backups:** Database dumps and snapshot archives are encrypted using modern AEAD encryption (`age` / GPG) with retention-aligned backup pruning.

## Consequences

- Credentials cannot be intercepted through process listings (`ps aux`), `docker inspect`, or Docker Compose configuration dumps.
- Client streaming latency is minimized without frame stalling or burstiness.
- Edge logging preserves regulatory privacy without leaking access tokens.
