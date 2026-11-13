# Privacy & Compliance Notes: GDPR, BIPA & Surveillance Data Governance

This document describes the privacy-by-design principles, regulatory compliance mappings (GDPR, CCPA/CPRA, Illinois BIPA), and data minimization controls enforced in the Border-AI surveillance platform.

---

## 1. Regulatory Context

Surveillance platforms handle sensitive personal data, including facial images, physical appearances, geographic movement patterns, and vehicle license plates.

| Regulation | Applicable Mandate | Platform Implementation |
|---|---|---|
| **GDPR Art. 5(1)(c)** | Data Minimisation | Role-based evidence redaction: non-investigative users (`VIEWER`) cannot access raw face/person crops. |
| **GDPR Art. 5(1)(e)** | Storage Limitation | Automatic rolling retention policy for snapshots and raw detection vectors (30-day default). |
| **GDPR Art. 17 / 20** | Right to Erasure / Portability | Specific purge APIs and export functions gated by strict `evidence:export` permission. |
| **GDPR Art. 32** | Security of Processing | AES-256-GCM encryption of camera credentials and hash-chained audit trails. |
| **Illinois BIPA (740 ILCS 14/)** | Biometric Information Privacy | Watchlist biometric embeddings are non-reversible feature vectors stored in dedicated tables with strict access auditing. |

---

## 2. Privacy-by-Design Controls

### 2.1 Role-Based Evidence Redaction
- **VIEWER Role:** Surveillance operators or monitoring staff with `VIEWER` role receive an obfuscated placeholder image (`image/svg+xml`) whenever requesting snapshots containing person detections.
- **OPERATOR Role:** Permitted to view incident crops for real-time situational verification without export rights.
- **INVESTIGATOR / ADMIN Roles:** Permitted full view and export capabilities, with every access sequentially recorded in the hash-chained audit log.

### 2.2 Watchlist Governance
- Watchlist entries require an explicit justification, legal authority basis, and authorized creator UUID.
- Automated audit log entry generated whenever a subject is enrolled, updated, or purged.
- Periodic re-certification workflow to avoid indefinite stale enrollments.

### 2.3 Cryptographic Logging & Auditability
- In compliance with accountability mandates, all queries against person detection records and watchlist matches are hashed and timestamped.
- Tamper-evident chaining guarantees that forensic inquiries cannot be manipulated or retroactively purged by operators.
