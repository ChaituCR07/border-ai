# ADR 0030 — Notification Policy: Content Delivery, Rate Limiting, and Privacy Guardrails

## Status
Accepted

## Context
Automated email alerts deliver actionable intelligence outside the secure perimeter of the Border-AI application. Transmitting unvetted images, unredacted personal identifiers, or unconstrained email volume introduces substantial legal, security, and operational hazards:
1. Leaking biometric face imagery or personal photographs over unencrypted email channels.
2. Email header injection exploits (`\r\n` injection) that compromise mail relays.
3. Notification floods during sensor noise or sustained threat incidents that saturate recipient inboxes.
4. Internal operational notes leaking to unintended parties.

Strict governance policies, privacy guardrails, and anti-flooding controls must be enforced by construction.

## Decisions

1. **Privacy by Construction for Person-Related Alerts (Invariant I7):**
   - Alerts with `object_class === 'person'`, event types `['FACE_MATCH', 'REID_CANDIDATE', 'WATCHLIST_PERSON']`, or metadata flag `person_related === true` **strictly never attach or link snapshot images** in notification emails.
   - The snapshot processor enforces this rule deterministically:
     ```ts
     if (options.personRelated) {
       return null; // Enforce Invariant I7
     }
     ```
   - Vehicle-related alerts are permitted to attach downscaled snapshots showing vehicular context, preserving evidence utility while upholding biometric privacy laws.

2. **Snapshot Image Downscaling and EXIF Stripping:**
   - Permitted snapshots are processed using `sharp` prior to MIME attachment.
   - Images are downscaled to a maximum bounding box of $640 \times 360\text{ px}$ with JPEG quality 75.
   - All EXIF metadata (camera serial numbers, GPS tags, device fingerprints) is permanently stripped.
   - Email payloads never exceed 300 KB, ensuring rapid mobile rendering and cellular data conservation.

3. **Anti-Flooding Cooldowns and Priority Upgrade Bypass:**
   - Notifications are grouped by route and subject key:
     - Vehicle alerts: group key is `plate`.
     - Non-vehicle alerts: group key is `camera_id:event_type`.
   - Subsequent alerts within the route's cooldown window ($300\text{s}$ default) are suppressed (`status = 'SKIPPED'`, `skip_reason = 'cooldown'`).
   - **Priority Upgrade Bypass:** If a new alert arrives for an active group with a higher priority than the preceding alert in that group (e.g. escalating from `HIGH` to `CRITICAL`), the cooldown is immediately bypassed to ensure urgent threats are communicated without delay.

4. **Sliding-Window Per-Recipient Rate Limiting:**
   - Workers enforce an in-memory sliding-window rate limiter per recipient email address.
   - Default limit: $\le 6$ emails per recipient per 60-second window.
   - When the limit is reached, notifications are deferred by 30 seconds without incrementing their failure attempt counter.

5. **Strict Header Sanitization and HTML Escaping:**
   - All dynamic strings inserted into email headers (`Subject`, `To`, `From`) are stripped of `\r` and `\n` characters, completely eliminating CRLF email injection vulnerabilities.
   - Dynamic HTML bodies escape characters `&`, `<`, `>`, `"`, and `'`.
   - Plain-text alternatives are generated alongside HTML bodies to ensure full accessibility across legacy email clients.

6. **Admin Delivery Log Recipient Masking:**
   - The administrative notification log (`GET /api/notifications`) masks recipient email addresses by default (`j***e@example.org`).
   - Unmasked addresses are returned only when an Administrator explicitly passes query parameter `reveal=1`.
   - Every `reveal=1` request is audited in `api_audit_log` with the administrator's actor identity.

7. **Internal Resolution Notes Secrecy:**
   - Operators may record internal forensic notes when resolving an alert (`resolution_note`).
   - Resolution notes are strictly confined to internal database audit trails. They are **never** included in notification emails, digests, or WebSocket broadcast payloads.

## Consequences
- Biometric and personal image data cannot leak outside the perimeter via notification channels.
- Inboxes are protected from storm events while remaining responsive to priority escalations.
- Complete regulatory compliance is established for email delivery and administrative logging.
