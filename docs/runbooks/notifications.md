# Notifications Operations & Troubleshooting Runbook

## 1. System Health & Diagnostics

### 1.1 Checking Outbox Queue & Planner Status
Run a status check against the administrative API:
```bash
curl -s -H "x-actor-role: ADMIN" http://localhost:4000/api/notifications/status | jq .
```
Expected output:
```json
{
  "data": {
    "enabled": true,
    "dry_run": false,
    "planner": {
      "running": true,
      "is_standby": false,
      "active": true
    },
    "queue": {
      "pending": 0,
      "sending": 0,
      "sent": 14,
      "failed": 0,
      "cancelled": 2,
      "skipped": 5
    }
  }
}
```

### 1.2 Inspecting Delivery Logs
To inspect recent delivery rows:
```bash
curl -s -H "x-actor-role: ADMIN" "http://localhost:4000/api/notifications?limit=20" | jq .
```
*Note:* Recipient emails are masked by default (`j***e@example.org`). To reveal unmasked recipient addresses for audit investigation:
```bash
curl -s -H "x-actor-role: ADMIN" "http://localhost:4000/api/notifications?limit=20&reveal=1" | jq .
```
*(Every reveal request is logged to `api_audit_log` with the administrator's identity).*

---

## 2. Common Incidents & Remediation

### 2.1 Queue Backlog / Stalled Notifications
**Symptom:** `queue.pending` count continues to increase; emails are not being received.

**Diagnosis:**
1. Check if the planner advisory lock is held:
   ```sql
   SELECT pid, locktype, objid, granted FROM pg_locks WHERE locktype = 'advisory' AND objid = 727001;
   ```
2. Verify SMTP connection:
   ```bash
   nc -zv localhost 1025
   ```
3. Check worker logs in `border-ai-backend`:
   ```bash
   docker compose logs backend | grep -i "worker"
   ```

**Remediation:**
- If Mailpit or SMTP is down, start the mailpit container:
  ```bash
  docker compose up -d mailpit
  ```
- If notifications were deferred by per-recipient rate limits, workers will automatically resume dispatch on the next 30-second window.

### 2.2 Re-Dispatching Failed Notifications
To retry a notification that permanently failed (e.g. following an upstream SMTP recovery):
```bash
curl -X POST -H "x-actor-role: ADMIN" http://localhost:4000/api/notifications/retry/<notification_id>
```
Eligible statuses for retry are `FAILED` and `CANCELLED`. Successful retry resets `status = 'PENDING'`, `attempts = 0`, and schedules immediate dispatch.

### 2.3 Emergency Kill-Switch Activation
If external relays are compromised or an email loop occurs, immediately disable notification dispatch:
```bash
# In backend .env or deployment environment:
NOTIFICATIONS_ENABLED=false
```
Or restart the backend with the environment variable set. In-flight tasks will pause and pending rows will remain safely buffered in the PostgreSQL outbox.

---

## 3. Configuration Validation
To validate `configs/notifications.json` before deploying:
```bash
npm --prefix backend run notifications:check
```
Exit code `0` confirms route syntax, regex rules, allowed recipient domains, and escalation timings are valid.
