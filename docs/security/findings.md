# Security Assessment & Hardening Findings (Day 26)

This document registers the security findings identified during the Day 26 threat modeling and automated security testing, along with the implemented mitigations and verification tests.

---

## Findings Summary

| ID | Title | Severity | Status | Verification Test |
|---|---|---|---|---|
| **FIND-01** | Anonymous MJPEG stream access on engine port 8001 | High | **Remediated** | `tests/test_stream_auth.py`, `tests/security/stream-token.test.ts` |
| **FIND-02** | Implicit route authorization (fail-open risk) | Critical | **Remediated** | `backend/tests/security/deny-by-default.test.ts` |
| **FIND-03** | Plaintext RTSP camera passwords stored in database | High | **Remediated** | `backend/tests/security/vault.test.ts`, `tests/test_vault.py` |
| **FIND-04** | User enumeration via password hashing timing discrepancy | Medium | **Remediated** | `backend/tests/security/passwords.test.ts` |
| **FIND-05** | Refresh token theft & replay across sessions | High | **Remediated** | `backend/tests/security/sessions-rotation.test.ts` |
| **FIND-06** | Access token exfiltration risk via `localStorage` XSS | Medium | **Remediated** | `frontend/test/auth.test.ts` |
| **FIND-07** | Administrator self-demotion or self-disable causing lockout | High | **Remediated** | `backend/tests/security/users-manage.test.ts` |
| **FIND-08** | Unauthorized viewer access to raw facial/person crops | Medium | **Remediated** | `backend/tests/security/snapshots-security.test.ts` |
| **FIND-09** | CSRF vulnerability on cookie-bearing refresh endpoint | Medium | **Remediated** | `backend/tests/security/headers-csrf.test.ts` |
| **FIND-10** | Tampering risk of API audit records | High | **Remediated** | `backend/tests/security/audit-chain.test.ts` |

---

## Detailed Finding Descriptions & Mitigations

### FIND-01: Anonymous MJPEG Stream Access
- **Risk:** Attackers on the local network could directly poll MJPEG video feeds from the engine without authentication.
- **Mitigation:** Generated short-lived EdDSA signed stream tokens (`stream:live`) verified natively by the Python engine using public key cryptography before streaming video frames.

### FIND-02: Fail-Open Route Authorization
- **Risk:** New API endpoints added by developers could accidentally remain public if security checks were forgotten.
- **Mitigation:** Implemented a strict `onRoute` hook in Fastify that throws an error at application boot if an endpoint is missing an explicit permission or `{ public: true }` tag.

### FIND-03: Plaintext RTSP Camera Credentials
- **Risk:** Database exfiltration or read-only SQL injection would expose raw camera administrative passwords.
- **Mitigation:** Implemented an AES-256-GCM credential vault with 12-byte IVs, sealing credentials with the unique `camera_id` as Authenticated Additional Data (AAD) to prevent vector reuse across cameras.

### FIND-04: User Enumeration via Timing Attacks
- **Risk:** Timing difference between immediate rejection for non-existent users vs Argon2id verification for existing users allowed username harvesting.
- **Mitigation:** Implemented constant-time dummy hash computation on non-existent usernames, normalizing timing response across both branches.

### FIND-05: Refresh Token Replay & Theft
- **Risk:** Stolen refresh tokens could be reused indefinitely to mint fresh access tokens.
- **Mitigation:** Implemented single-use refresh token rotation with cryptographic family tracking (`family_id`). Reusing an old refresh token instantly revokes the entire family.
