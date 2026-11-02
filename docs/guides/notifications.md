# Alert Generation & Notification Dispatch Operator Guide

## 1. Overview
The Border-AI Notification Dispatch Engine automates alerting for high and critical threats across perimeter surveillance cameras. Using a decoupled transactional outbox, PostgreSQL session advisory locks, and sharp image processing, it routes actionable intelligence to operations desks, supervisors, and duty officers while strictly preserving biometric privacy.

---

## 2. Notification Routing & Cooldown Policies

### 2.1 Route Evaluation
Alerts are evaluated against configured routes in `configs/notifications.json` by matching:
- **Priority:** `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
- **Camera ID (optional):** Specific camera checkpoints (e.g. `CAM-03`).
- **Event Type (optional):** Specific threat classifications (e.g. `RESTRICTED_ZONE_ENTRY`).

### 2.2 Cooldowns and Grouping
To avoid alert flooding during persistent incidents, notifications are grouped:
- **Vehicular Alerts:** Grouped by license plate string (`plate`).
- **Other Alerts:** Grouped by camera and event type (`camera_id:event_type`).

If an alert occurs within the route's cooldown window (default: 300 seconds) for the same subject key, it is suppressed as `SKIPPED (cooldown)`.

### 2.3 Priority Upgrade Bypass
If an existing group receives a subsequent alert with a higher priority than the preceding alert (for example, escalating from `HIGH` to `CRITICAL`), the cooldown is immediately bypassed to ensure critical developments are never delayed.

---

## 3. Privacy by Construction Guardrails

### 3.1 Strict Biometric Redaction (Invariant I7)
- Any alert involving individuals (`object_class === 'person'`, event types such as `FACE_MATCH`, `REID_CANDIDATE`, `WATCHLIST_PERSON`, or metadata flag `person_related === true`) **strictly never includes snapshots in email notifications**.
- Email templates for person-related alerts omit the snapshot and provide a secure link to the command center workbench.

### 3.2 Evidence Snapshot Processing
- Permitted vehicular snapshots are downscaled to $\le 640\text{ px}$ width at JPEG quality 75.
- All EXIF metadata (camera serial numbers, precise timestamps, GPS coordinates) is stripped.
- MIME attachment size is capped under 300 KB.

---

## 4. Operational Workflows

### 4.1 Deep Link Navigation (`/?alert=<id>`)
- Every notification email includes a direct link: `/?alert=<alert_id>`.
- Opening the deep link:
  1. Automatically selects the relevant camera in the command center.
  2. Opens the Evidence Snapshot drawer with full event metadata and threat factors.
  3. Displays an informational banner if another officer has already acknowledged or resolved the alert.

### 4.2 Resolving Alerts
- Operators can resolve alerts directly from the drawer:
  1. Click **Resolve Alert...**
  2. Select the resolution disposition:
     - `FALSE_POSITIVE`: Benign event or detector misclassification.
     - `VERIFIED_THREAT`: Confirmed threat addressed by perimeter patrol.
     - `RESOLVED_OTHER`: Routine checkpoint clearance or administrative handoff.
  3. Optionally enter an internal resolution note (strictly internal, never emailed).
  4. Confirming resolution transitions the alert to `RESOLVED` and automatically cancels any scheduled escalation notifications.

---

## 5. Local Development & Staging Testing

In local environments, emails are routed to **Mailpit**:
- **SMTP Server:** `localhost:1025`
- **Mailpit Web UI:** [http://localhost:8025](http://localhost:8025)

Inspect HTML and plain-text layouts, headers, and attachments directly in the Mailpit web interface without external email credentials.
