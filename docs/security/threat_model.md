# Border-AI Threat Model (STRIDE-lite)

**Date:** 2026-11-13  
**Status:** Approved  
**Scope:** Border-AI Video Intelligence Platform (Node.js API, Python Engine, Redis, PostgreSQL, MediaMTX, Frontend)  
**Standard:** OWASP ASVS 4.0 & NIST SP 800-63B Alignment  

---

## 1. System Overview & Trust Boundaries

The Border-AI platform ingests real-time RTSP video feeds from deployed border cameras, performs object detection (persons, vehicles), license plate recognition (ANPR), and multi-camera trajectory tracking, publishing structured events to Redis Streams and PostgreSQL. Operators, investigators, viewers, and administrators interact with the system via a Web UI and REST/WebSocket APIs.

```
                      +---------------------------------------+
                      |         Untrusted Zone (Public)       |
                      |   - External Attacker                 |
                      |   - Malicious RTSP Sender             |
                      +-------------------+-------------------+
                                          |
                        [Network Boundary: Firewalls / TLS]
                                          |
                                          v
                      +---------------------------------------+
                      |       Demilitarized / Ingest Zone     |
                      |   - MediaMTX RTSP Server (:8554)      |
                      +-------------------+-------------------+
                                          |
                                          v
+-------------------------+   [Stream Auth]   +---------------------------+
|   Operator / Viewer /   | ----------------> |  Python Inference Engine  |
|  Investigator / Admin   |                   |  - MJPEG Stream (:8001)   |
|  (Web Browser / Client) |                   |  - Internal Metrics       |
+------------+------------+                   +-------------+-------------+
             |                                              |
      [Bearer JWT / Cookie]                       [XADD Events / Alerts]
             |                                              |
             v                                              v
+-------------------------+                   +---------------------------+
|    Backend REST API     | <---------------> |   Redis (Streams / PubSub)|
|    - Fastify (:4000)    |                   +---------------------------+
|    - Deny-by-default    |                                 ^
|    - AuthN / RBAC       |                                 |
+------------+------------+                       [XREADGROUP / Worker]
             |                                              |
       [SQL Queries]                          +-------------+-------------+
             v                                |  PostgreSQL Ingestion Sink|
+-------------------------+                   +-------------+-------------+
|  PostgreSQL Database    | <-------------------------------+
|  - Users / Sessions     |
|  - Events / Detections  |
|  - Tamper-Evident Audit |
+-------------------------+
```

### Trust Zones & Boundaries
1. **Zone 0 (External / Client):** Web browsers and network clients. Untrusted.
2. **Zone 1 (API Edge):** Fastify backend server listening on port 4000. Handles TLS termination (production), auth verification, rate limiting, and CORS/CSRF defense.
3. **Zone 2 (Engine & Media Service):** Python detection pipeline and MediaMTX server. Verified streams via EdDSA tokens.
4. **Zone 3 (Core Data Store):** PostgreSQL and Redis data stores, accessible only via isolated internal network interfaces with per-service credential roles.

---

## 2. Protected Assets

| Asset ID | Asset Description | Confidentiality | Integrity | Availability |
|---|---|:---:|:---:|:---:|
| **A-1** | Live video feeds & MJPEG streams | High | High | High |
| **A-2** | Forensic snapshots & person evidence | High (PII) | High | Medium |
| **A-3** | License plate records (ANPR) | High | High | Medium |
| **A-4** | Watchlist configurations (targets) | Strict (Need-to-Know) | Strict | High |
| **A-5** | Security alert notifications & escalations | Medium | Strict | Critical |
| **A-6** | System credentials (RTSP passwords, JWT private keys, master keys) | Critical | Critical | Critical |
| **A-7** | Tamper-evident audit logs | High | Critical | High |
| **A-8** | Detection thresholds & rule configuration | High | Strict | High |

---

## 3. Threat Actors & Capabilities

1. **Unauthenticated External Attacker (AT-1):** Has network visibility to public-facing API/web ports. Attempts brute-force credential guessing, token forgery, injection, clickjacking, and DoS attacks.
2. **Malicious / Compromised Camera (AT-2):** Controlled RTSP source sending malformed video streams to exploit decoder vulnerabilities (FFmpeg/OpenCV memory corruption).
3. **Curious or Malicious Insider (AT-3):**
   - *Viewer:* Attempts horizontal privilege escalation to read person evidence or access admin configurations.
   - *Operator:* Attempts unauthorized plate searches or snooping on target watchlists.
   - *Investigator:* Attempts mass export without justification or modifying operational rules.
4. **Rogue Administrator (AT-4):** Attempts to delete or alter historical audit logs, erase evidence, or demote the last remaining active administrator.
5. **Supply Chain Adversary (AT-5):** Injects malicious code into upstream npm/Python packages or container images.

---

## 4. STRIDE-lite Threat Analysis & Mitigations

### 4.1 Spoofing (Identity & Tokens)
- **T-S1: Forged JWT Access Token:** Attacker modifies payload to grant `ADMIN` role or changes algorithm to `none` / HMAC using public key.
  - *Mitigation:* Asymmetric EdDSA (Ed25519) algorithm strictly enforced via allow-list; rejects `alg: none`, HMAC keys, or unknown key IDs (`kid`); local JWKS verification without dynamic remote URL resolution (`jku`/`x5u`).
- **T-S2: Stolen Refresh Token via XSS:** Attacker executes client-side script to harvest stored tokens.
  - *Mitigation:* Access tokens held strictly in-memory (never `localStorage` or `sessionStorage`); refresh tokens stored in `HttpOnly; Secure; SameSite=Strict; Path=/api/auth` cookies.
- **T-S3: Token Replay After Logout or Session Revocation:** Attacker replays captured token.
  - *Mitigation:* Short access token TTL (10 minutes); server-side session checks with 5-second caching; user `token_version` invalidates all issued tokens on password change or account disable.

### 4.2 Tampering (Data & Audit Integrity)
- **T-T1: Audit Log Tampering:** Database administrator or compromised service updates/deletes audit rows to hide malicious queries.
  - *Mitigation:* Tamper-evident hash-chained audit log where each entry calculates `hash = SHA-256(prev_hash || canonical_json(entry))`; database trigger prohibits `UPDATE` and `DELETE`; verification CLI (`npm run audit:verify`) asserts chain continuity.
- **T-T2: Configuration Tampering (Silencing Detection):** Attacker raises alert thresholds to hide border breaches.
  - *Mitigation:* Admin-only configuration endpoints with JSON schema validation, version history, mandatory change reason, and automated audit records.
- **T-T3: Camera Credential Exposure:** Plaintext RTSP passwords extracted from database dumps.
  - *Mitigation:* AES-256-GCM encrypted credential vault with authenticated associated data (AAD = `camera_id`) and master keys injected via environment/secret files.

### 4.3 Repudiation
- **T-R1: Unaudited Surveillance Queries:** Investigator tracks a target's vehicle movements without recorded justification.
  - *Mitigation:* Investigation person search, trajectory journey, and export endpoints require mandatory `purpose` field; all search queries and exports are recorded in tamper-evident audit log with actor ID, IP address, and timestamp.

### 4.4 Information Disclosure
- **T-I1: Viewer Access to Person Evidence:** Unauthorized viewer accesses person facial crops or biometric snapshots.
  - *Mitigation:* Granular RBAC (`evidence:view`); snapshot endpoint serves a generic placeholder image for person-related evidence when requested by `VIEWER` role.
- **T-I2: Open MJPEG Stream Access:** External actor views live border cameras by guessing stream URLs (`:8001/cam/cam-01.mjpg`).
  - *Mitigation:* Single-use, short-lived EdDSA stream tokens (`typ=stream+jwt`, 60-second connection TTL, 15-minute max session) verified directly by Python engine with public key.
- **T-I3: User Enumeration on Login:** Attacker tests email addresses by observing differing error messages or response timing.
  - *Mitigation:* Uniform error message (`401 INVALID_CREDENTIALS`) across all authentication failures; dummy Argon2id hash verification on unknown users ensures constant-time execution.

### 4.5 Denial of Service (DoS)
- **T-D1: Argon2 Password Hashing Flood:** Flooding login endpoint with complex passwords exhausts server CPU.
  - *Mitigation:* Pre-hashing IP rate limiting, concurrency semaphore limiting concurrent Argon2id operations to 3, and strict request body size caps.
- **T-D2: WebSocket Connection Exhaustion:** Opening thousands of persistent WebSockets exhausts backend file descriptors.
  - *Mitigation:* Single-use 128-bit ticket required for WebSocket handshake (30s TTL, deleted on connect); origin verification; per-session connection limits.

### 4.6 Elevation of Privilege
- **T-E1: Unprotected REST Route:** Developer adds an admin route without explicitly attaching security guards.
  - *Mitigation:* Deny-by-default architecture: Fastify `onRoute` hook verifies every route declares either `config.permission` or `config.public = true`; server refuses to start if any route is unprotected.
- **T-E2: Self-Demotion / Last Admin Lockout:** Rogue admin demotes or deletes their own account, locking out administrative access.
  - *Mitigation:* Safety guard asserts active administrator count > 1 before allowing deletion or demotion of any admin account.

---

## 5. Misuse & Abuse Cases (Automated Test Backlog)

1. **Abuse 1:** Operator attempts to read the watchlist (`GET /api/watchlist`) -> Expect `403 FORBIDDEN`.
2. **Abuse 2:** Viewer attempts to download person snapshot (`GET /api/snapshots/...`) -> Returns redacted placeholder image.
3. **Abuse 3:** Investigator exports data without `purpose` header -> Expect `400 BAD_REQUEST`.
4. **Abuse 4:** Admin attempts to delete the last active administrator -> Expect `400 / 409 CONFLICT`.
5. **Abuse 5:** Attacker replays refresh token cookie after rotation -> Triggers token family revocation, audits `REFRESH_REUSE_DETECTED`, returns `401`.
6. **Abuse 6:** Attacker presents JWT with header `{"alg": "none"}` -> Expect `401 UNAUTHENTICATED`.
7. **Abuse 7:** Client attempts WebSocket connection without valid ticket -> Rejected `401` during upgrade.
8. **Abuse 8:** Client uses API JWT token to access engine MJPEG stream -> Rejected `401 / 403` due to audience and type mismatch.
