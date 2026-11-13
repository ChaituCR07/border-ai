# OWASP ASVS 4.0 Verification Mapping

This matrix maps Border-AI system components and Day 26 security implementations against the **OWASP Application Security Verification Standard (ASVS) 4.0 Level 2**.

---

| ASVS Section | Requirement Category | Implementation & Verification | Status |
|---|---|---|---|
| **V1.1** | Threat Modeling | STRIDE-lite threat model documented in `docs/security/threat_model.md` and attack surface registered in `docs/security/surface.md`. | :white_check_mark: Verified |
| **V1.4** | Access Control Architecture | Deny-by-default `onRoute` guard (`backend/src/security/route-guard.ts`). Automated RBAC matrix generator and tests. | :white_check_mark: Verified |
| **V2.1** | Password Security | NIST SP 800-63B compliant password policy (min 12 chars, entropy checks, common password blocklist). | :white_check_mark: Verified |
| **V2.4** | Credential Storage | Argon2id hashing with $m=64\text{MB}, t=3, p=4$. Dummy-hash timing equalization preventing user enumeration. | :white_check_mark: Verified |
| **V2.8** | Token Authentication | RFC 8032 Ed25519 (EdDSA) asymmetric JWT tokens with JWKS endpoint (`/.well-known/jwks.json`). Short-lived (15 min). | :white_check_mark: Verified |
| **V3.2** | Session Management | Rotating refresh tokens with family tracking and reuse fraud detection (`backend/src/modules/auth/sessions.ts`). | :white_check_mark: Verified |
| **V3.3** | Session Termination | Complete logout invalidating session family. `token_version` check on all tokens allowing instant global revocation. | :white_check_mark: Verified |
| **V4.1** | General Access Control | All 35+ API routes mapped explicitly to granular permissions. Unmapped routes throw during server bootstrap. | :white_check_mark: Verified |
| **V4.2** | Operation Level Access | Last-admin protection preventing demotion or disabling of sole admin user. | :white_check_mark: Verified |
| **V4.3** | Contextual Access Control | Person evidence redaction: VIEWER role receives redacted placeholder SVG instead of raw surveillance images. | :white_check_mark: Verified |
| **V5.1** | Input Validation | Zod schema validation across all request parameters, bodies, and query strings. Disallows unexpected properties. | :white_check_mark: Verified |
| **V6.2** | Algorithms | AES-256-GCM authenticated encryption for camera credentials. Key IDs and 12-byte IVs with camera ID as AAD. | :white_check_mark: Verified |
| **V7.1** | Log Integrity | Tamper-evident hash-chained audit logging (`SHA-256(prev_hash ‖ row)`). `npm run audit:verify` validation. | :white_check_mark: Verified |
| **V7.2** | Sensitive Data Logging | Automated Pino log redaction for authorization headers, cookies, passwords, and tokens. | :white_check_mark: Verified |
| **V8.3** | Sensitive Data Protection | Tokens stored strictly in-memory in frontend client. Zero token persistence to `localStorage` or `sessionStorage`. | :white_check_mark: Verified |
| **V9.1** | Communications Security | WebSocket single-use ticket mechanism (`backend/src/realtime/tickets.ts`) and engine stream signature tokens. | :white_check_mark: Verified |
| **V13.1** | API Security | Double-submit CSRF protection for cookie endpoints (`/api/auth/refresh`), CORS origin allow-list, CSP, and COOP/CORP headers. | :white_check_mark: Verified |
| **V14.1** | Build and Configuration | Strict separation of development vs production security modes. Automated claim checker (`check_claims.py`). | :white_check_mark: Verified |
