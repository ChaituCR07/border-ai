# Border-AI Media Privacy & Redaction Review Log

This document records the privacy audit, OCR redaction screening, and data sanitation sign-offs conducted on all public screenshots, diagrams, and demonstration videos (ADR 0055).

---

## 1. Audit Scope & Verification Policy
- **Review Date:** 2026-11-15
- **Lead Reviewer:** Chaitanya Medam (ChaituCR07)
- **Status:** **APPROVED FOR PUBLIC PORTFOLIO RELEASE**

### Screening Criteria
1. **Zero Real Face Biometrics:** All human subjects originate from synthetic pedestrian footage or research test sets; no real private citizen faces are exposed.
2. **Zero Real Vehicle Registration Plates:** All license plates visible across UI cards, tables, and stream overlays are verified synthetic look-alikes (`KA01AB1234`, `MH12DE5678`).
3. **Zero Leaked Credentials:** Address bars, browser developer tools, and authorization headers are scrubbed. No JWT bearer tokens, Argon2id hashes, or master vault keys appear in any image.
4. **Metadata Sanitization:** EXIF, GPS coordinates, device serial numbers, and camera firmware strings have been purged via image hygiene pipelines.

---

## 2. Screenshot File Audit Matrix

| File | Viewport / Route | OCR PII Scan | Token / Secret Scan | Status |
|---|---|:---:|:---:|:---:|
| `01-login.png` | `/login` | Clean (0 PII) | Clean (No auto-fill passwords) | **PASS** |
| `02-command-center-grid.png` | `/dashboard` | Clean (Synthetic plates only) | Clean (No auth headers) | **PASS** |
| `03-critical-alert-toast.png` | Toast notification | Clean (Synthetic target plate) | Clean | **PASS** |
| `04-alert-drawer-factor-checklist.png` | Evidence drawer | Clean (Redacted vehicle crop) | Clean | **PASS** |
| `05-scenario-1-card.png` | Intrusion alert card | Clean (Foot-point coordinates) | Clean | **PASS** |
| `06-investigation-results.png` | `/investigation` | Clean (Synthetic search terms) | Clean | **PASS** |
| `07-cross-camera-journey-view.png`| `/investigation/journey` | Clean (Synthetic timeline) | Clean | **PASS** |
| `08-mailpit-email-notification.png`| Mailpit web UI | Clean (Local domain: `@border.local`)| Clean | **PASS** |
| `09-system-health-status.png` | `/system/status` | Clean (Container names only) | Clean | **PASS** |
| `10-admin-audit-log.png` | `/admin/audit` | Clean (Hashed identities) | Clean (SHA-256 chain hashes only)| **PASS** |
| `hero.gif` | Live alert flow | Clean (Synthetic stream video) | Clean | **PASS** |
