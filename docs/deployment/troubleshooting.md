# Border-AI Troubleshooting & Operational FAQ

This guide indexes common operational failure modes, diagnostic commands, and resolution runbooks for the Border-AI Docker deployment.

---

## 1. Quick Diagnostic Checklist

When encountering stack issues, run these diagnostic commands:

```bash
# Check container status and health
make compose-ps

# View live error logs across all services
docker compose logs -f --tail=100

# Inspect specific failing service
docker compose logs backend
docker compose logs ai-engine
docker compose logs postgres

# Run automated deployment hardening and isolation checks
make test-compose
```

---

## 2. Common Pitfalls & Resolutions (K1–K28)

### Category A: Permissions & Volume Mounts
- **K1: Postgres permission denied on `/var/lib/postgresql/data`**
  - *Cause:* Persistent volume created with host root ownership.
  - *Resolution:* Postgres runs as UID 999 (`postgres`). Ensure host directory or named Docker volume permissions match UID 999.
- **K2: Snapshots volume `/var/lib/border-ai/snapshots` read-only or permission denied**
  - *Cause:* Shared volume ownership mismatch between `backend` (UID 10001) and `ai-engine` (UID 10002).
  - *Resolution:* The entrypoint scripts automatically align permissions via group GID 10001, or run `chmod -R 775 /var/lib/border-ai/snapshots`.
- **K3: Secrets files cannot be read (`EACCES` / `Permission denied`)**
  - *Cause:* Secrets directory created with `0700` and individual files restricted to root.
  - *Resolution:* Run `chmod 644 secrets/jwt_public_key` and ensure non-root container users can read required secrets mounted by Compose.

### Category B: Networking & Proxy
- **K4: 502 Bad Gateway from Nginx**
  - *Cause:* Upstream backend or frontend container is starting up, unhealthy, or crashed.
  - *Resolution:* Check `docker compose ps`. Wait for `backend` to transition from `(starting)` to `(healthy)`.
- **K5: Browser displays `NET::ERR_CERT_AUTHORITY_INVALID`**
  - *Cause:* Self-signed TLS certificate generated for `localhost` during quickstart.
  - *Resolution:* For development, bypass browser warning by clicking Advanced -> Proceed, or install `certs/edge.crt` into the OS root trust store. For production, replace `certs/edge.crt` with an authoritative CA certificate (e.g. Let's Encrypt).
- **K6: WebSocket connection fails (`1006 abnormal closure`)**
  - *Cause:* Missing `Upgrade` / `Connection` headers in intermediary proxy or firewall.
  - *Resolution:* Verify Nginx includes `proxy_set_header Upgrade $http_upgrade` and `proxy_set_header Connection "upgrade"` (configured in `docker/nginx/snippets/proxy-common.conf`).
- **K7: MJPEG live video stream freezes or buffers indefinitely**
  - *Cause:* Proxy buffering enabled or HTTP/1.1 connection limit reached.
  - *Resolution:* Nginx configuration sets `proxy_buffering off` and `proxy_read_timeout 3600s` for `/api/v1/streams/` endpoints.

### Category C: Database & Secrets
- **K8: Backend container exits with `FATAL: password authentication failed for user "border_backend"`**
  - *Cause:* `secrets/backend_db_password` does not match the password stored in PostgreSQL.
  - *Resolution:* Re-run `db-init` service: `docker compose run --rm db-init`.
- **K9: Database migration fails on bootstrap**
  - *Cause:* Database container not fully healthy when migrations run.
  - *Resolution:* Ensure Compose `depends_on: postgres: { condition: service_healthy }` is respected.
- **K10: Redis ACL authentication error (`NOAUTH Authentication required` or `WRONGPASS`)**
  - *Cause:* `users.acl` hash mismatch or wrong password in `secrets/redis_backend_password`.
  - *Resolution:* Regenerate ACL file: `scripts/gen_secrets.sh --force` and restart Redis.

### Category D: AI Engine & Models
- **K11: Engine fails with `Model weight verification error: SHA-256 mismatch`**
  - *Cause:* Model weight file corrupted or partially downloaded.
  - *Resolution:* Run `python3 engine/tools/fetch_models.py --force` to re-download official weights and verify against `configs/models.lock.json`.
- **K12: CUDA out of memory (OOM)**
  - *Cause:* Insufficient VRAM allocated when processing high-resolution RTSP streams concurrently.
  - *Resolution:* Reduce `fps_target` in `configs/cameras.json`, or configure batch sizing in `docker-compose.gpu.yml`.
- **K13: RTSP connection refused from `mediamtx`**
  - *Cause:* `cctv-sim` simulator or camera feed not publishing to MediaMTX.
  - *Resolution:* Check `docker compose logs mediamtx` and verify camera paths.

---

## 3. Safe Factory Reset

To wipe all local platform data, secrets, volumes, and start completely fresh:

```bash
# Full reset (requires explicit confirmation)
make reset CONFIRM=yes
```
