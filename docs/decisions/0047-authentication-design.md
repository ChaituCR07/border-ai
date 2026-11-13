# 47. Authentication Design: EdDSA Access Tokens, Rotating Refresh Tokens, and Argon2id Hashing

Date: 2026-11-13  
Status: Accepted  

## Context

The Border-AI platform previously operated with authentication stubs, returning static administrative identities in development mode while enforcing a production startup guard. To protect live border surveillance telemetry, forensic snapshots, and operational watchlists, the system requires a production-grade authentication architecture adhering to NIST SP 800-63B and OWASP ASVS 4.0 guidelines.

Key requirements:
1. Short-lived access credentials that can be verified asynchronously and efficiently across microservices (including the Python inference engine) without sharing private signing keys.
2. Long-lived session management with rapid revocation and protection against token theft.
3. Password storage resilient to offline dictionary attacks and specialized GPU cracking hardware.
4. Timing-attack immunity to prevent user enumeration.

## Decisions

### 1. Token Architecture

The platform adopts a multi-tier token strategy:

| Token Type | Cryptographic Mechanism | Lifetime | Storage Location | Claims / Attributes |
|---|---|---|---|---|
| **Access Token** | JWT, **EdDSA (Ed25519)**, `kid` header | 10 minutes | In-memory only (React state) | `iss=border-ai`, `aud=border-ai-api`, `sub=user_id`, `role`, `sid=session_id`, `ver=token_version`, `iat`, `exp`, `jti` |
| **Refresh Token** | Opaque 256-bit entropy (`base64url`) | Sliding 8 hours (idle), 12 hours absolute | `HttpOnly; Secure; SameSite=Strict; Path=/api/auth` Cookie | SHA-256 hash stored in DB; rotated on every use; token family revocation on reuse |
| **WebSocket Ticket** | Opaque 128-bit entropy (`base64url`) | 30 seconds (single-use) | Ephemeral query parameter during HTTP upgrade | Bound to `user_id`, `session_id`, and `role` |
| **Stream Token** | JWT, EdDSA (Ed25519) | 60 seconds (handshake), 15 min max duration | URL query parameter for `<img src>` | `typ=stream+jwt`, `iss=border-ai`, `aud=border-ai-stream`, `cam=camera_id`, `sub=user_id` |

### 2. EdDSA (Ed25519) Signing & Verification Rules
- **Asymmetric Signature:** Private key signs tokens in the Fastify backend; public keys are distributed to Python engine and public callers via `GET /.well-known/jwks.json`.
- **Strict Algorithm Allow-List:** Verifier accepts only `EdDSA`. Requests specifying `alg: "none"`, HMAC (`HS256`), or RSA algorithms are immediately rejected.
- **Header Hardening:** Remote JWKS references (`jku`, `x5u`, embedded `jwk`) are explicitly ignored; keys are resolved strictly against a local trusted key set.
- **Payload Constraints:** Maximum token size is capped at 4,096 bytes; clock skew tolerance is limited to 5 seconds.

### 3. Rotating Refresh Tokens & Multi-Tab Synchronization
1. Each refresh request rotates the refresh token: issues a new opaque token, updates `rotated_at`, and links the successor record (`replaced_by`).
2. **Grace Window (5s):** If a previously rotated token is presented within 5 seconds of its rotation timestamp, the server assumes a multi-tab race condition, issuing a fresh access token without invalidating the family or rotating the cookie again.
3. **Reuse Detection:** If an already-rotated token is presented outside the 5-second grace window, the system flags a token theft event (`REFRESH_REUSE_DETECTED`), immediately revokes the entire session family (`family_id`), and denies access (`401 UNAUTHENTICATED`).

### 4. Password Security & Anti-Enumeration Policy
- **Argon2id Algorithm:** Configured with baseline parameters (memory = 19 MiB, time = 2 iterations, parallelism = 1). Automatic rehash is triggered on login if stored PHC parameters fall below current security baseline.
- **Password Policy:** Minimum 12 characters, maximum 128 characters (NFKC normalized), rejected if present in the offline top-common password blacklist, equal to username/email, or matching any of the last 5 historical password hashes.
- **Anti-Enumeration:** Uniform response payload and status (`401 INVALID_CREDENTIALS`) across all authentication failures (unknown user, invalid password, disabled account). Unknown users are verified against an ephemeral dummy hash to maintain constant response timing.
- **Brute-Force Throttling:** Exponential backoff triggered after 5 consecutive failures per account/IP. Permanent lockout is avoided to prevent denial-of-service against legitimate users.

## Consequences

- Private keys remain isolated within backend memory or Docker secrets.
- Cross-service token verification in Python runs without network roundtrips to the DB.
- Browser storage cannot be raided for persistent refresh tokens via standard XSS.
