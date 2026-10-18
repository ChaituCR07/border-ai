# Biometrics & Identity Privacy Policy

This policy governs the biometric and identity analysis capabilities implemented in the `border-ai` platform (Day 10: Face Watchlist & Person Re-ID).

---

## 1. Core Principles & Safeguards

1. **Disabled by Default (`identity.enabled: false`):**
   The entire identity processing subsystem is inactive unless explicitly enabled via `--identity` or configuration override. At startup, a warning is emitted reminding operators of consent and legal compliance obligations.

2. **Strictly Consent-Gated Enrollment:**
   The enrollment engine enforces consent confirmation via `--consent-confirmed` in CLI tools and `consent_confirmed: bool` in library calls. Without explicit confirmation, the system throws `ConsentRequired` and refuses execution.

3. **Numeric Embeddings Only (Zero Image Storage):**
   The platform stores only L2-normalized floating-point embedding vectors (`float32` byte arrays), model names, and dimensions. **No face crops, person photos, or biometric images are ever persisted** in the database, file system, or event logs.

4. **Privacy-Preserving Event Streams:**
   Security event streams (`events.jsonl`, Redis Streams, WebSockets) contain only numeric scores, similarity values, bounding boxes, and anonymous internal IDs. Real names, descriptions, and person identities are omitted to prevent PII leakage across wide message buses. Authorized operators resolve identities inside the dashboard under Investigator/Admin roles.

5. **Human-in-the-Loop (`review` by Default):**
   Face matches and cross-camera Re-ID associations are treated strictly as **leads for human verification**, not definitive identifications. `allow_alert` is `false` by default, requiring human review for every biometric event.

---

## 2. Data Lifecycle & Deletion

- **Watchlist Entries:** Stored in PostgreSQL `watchlist` with `active = true`. Deactivation (`active = false`) soft-deletes the entry, stopping all future matches while preserving historical audit records.
- **Permanent Purge:** To delete an enrolled embedding permanently:
  ```sql
  UPDATE watchlist SET embedding = NULL, active = FALSE WHERE watchlist_id = <ID>;
  ```
- **Re-ID Short-Lived Gallery:** Appearance embeddings from camera tracks reside exclusively in volatile memory (`ReidGallery`) with a strict time-to-live (`gallery_ttl_s: 900`). Expired embeddings are automatically purged from memory.

---

## 3. Regulatory Compliance
Operators deploying facial analysis or biometric recognition must adhere to applicable regional regulations (e.g., EU AI Act, GDPR, CCPA/CPRA, and relevant national surveillance frameworks). Use is strictly restricted to authorized surveillance zones and consenting participants.
