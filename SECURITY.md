# Security Policy: Border-AI Surveillance Platform

Border-AI treats system security, privacy, and integrity as mission-critical. This document defines our vulnerability reporting procedures, supported versions, incident response timelines, and security posture.

---

## 1. Supported Versions

Security updates and patches are actively provided for the following releases:

| Version | Supported | Security Patch SLA |
|---|---|---|
| `1.0.x` (Current Day 26+) | :white_check_mark: Yes | Critical: < 24h, High: < 72h |
| `< 1.0.0` (Development) | :x: No | Community effort |

---

## 2. Reporting a Vulnerability

If you discover a security vulnerability, **DO NOT** open a public GitHub issue. Please report it privately through one of the following channels:

- **Email:** `security@border-ai.internal` (or repository security contact)
- **PGP Key Fingerprint:** `4A9F 12B8 9C34 E567 8901 2345 6789 ABCD EF01 2345`
- **Subject Line:** `[VULNERABILITY REPORT] <Component Name>: <Brief Description>`

### Please include in your report:
1. **Component affected:** API Backend, AI Engine, Stream Gateway, Frontend, or Database.
2. **Type of vulnerability:** e.g., Authentication bypass, Privilege Escalation, Path Traversal, Injection, Cryptographic Flaw.
3. **Step-by-step reproduction instructions:** Minimal curl commands, HTTP requests, or script to reproduce.
4. **Impact assessment:** What access or data an attacker can obtain.
5. **Proof of Concept (PoC):** Non-destructive test vector.

---

## 3. Vulnerability Response Timeline

We adhere to a strict coordinated vulnerability disclosure process:

1. **Acknowledgment:** Within 24 hours of report receipt.
2. **Assessment & Triage:** Within 48 hours, detailing severity (CVSS v3.1 score).
3. **Remediation & Patching:**
   - **Critical (CVSS 9.0–10.0):** Hotfix deployed within 24 hours.
   - **High (CVSS 7.0–8.9):** Patch deployed within 72 hours.
   - **Medium / Low (CVSS < 7.0):** Addressed in next scheduled sprint release.
4. **Disclosure:** Coordinated public disclosure 14 days after fix deployment, crediting the researcher.

---

## 4. Security Architecture Highlights

Border-AI implements defense-in-depth principles:
- **Asymmetric EdDSA (Ed25519) JWTs:** Public key verification with JWKS endpoint (`/.well-known/jwks.json`).
- **Argon2id Password Hashing:** Memory: 64MB, Passes: 3, Parallelism: 4 with dummy-hash timing attack mitigation.
- **Strict Deny-by-Default RBAC:** Start-up validation preventing unmapped endpoints.
- **AES-256-GCM Credential Vault:** Camera passwords sealed with unique camera ID as Authenticated Additional Data (AAD).
- **Tamper-Evident Hash-Chained Audit Log:** Sequential SHA-256 chaining with genesis link.
- **Single-Flight Refresh & In-Memory Tokens:** Tokens never stored in `localStorage` or `sessionStorage`.
