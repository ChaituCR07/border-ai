# Border-AI System Glossary: Terminology & Data Types

**Project:** Border-AI Video Intelligence Platform  
**Document:** System Nomenclature & Invariant Contracts  
**Status:** Canonical Reference

---

## 1. Priority vs. Severity

A critical architectural distinction across Border-AI services:

| Term | Context | Scope | Permitted Values | Contract Notes |
|---|---|---|---|---|
| **`priority`** | **Alerts** (`alerts` table, WebSocket `alert.*`, REST `/api/alerts/*`) | High-level operational urgency requiring human decision or escalation. | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Single source of truth is the threat tier derived from threat score ($0-100$). |
| **`severity`** | **Events** (`events` table, WebSocket `event.*`, raw pipeline envelopes) | Raw sensor classification urgency for an individual event detection. | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Computed per rule or detection classification prior to aggregation. |

> [!IMPORTANT]
> **Code Rule:** Never mix `priority` and `severity` within the same schema domain. The API exposes `priority` on all Alert DTOs and `severity` on raw Event records. Both map deterministically to the same score boundaries in `configs/threat_thresholds.json`.

---

## 2. Threat Tiers & Thresholds

| Tier | Threat Score Range | Operational Meaning | Default Notification Action |
|---|---|---|---|
| `LOW` | $0 \le \text{score} < 30$ | Informational observation | Logged to database only; no push notification. |
| `MEDIUM` | $30 \le \text{score} < 60$ | Anomalous behavior or watchlist notice | Surfaced in situational dashboard; no email. |
| `HIGH` | $60 \le \text{score} < 80$ | Multiple compounding risk factors | Live toast notification; periodic supervisor digest email. |
| `CRITICAL` | $80 \le \text{score} \le 100$ | Severe perimeter breach, known threat vehicle/person | Immediate control room alert, audio dispatch, instant email, 5-minute escalation. |

---

## 3. Alert Lifecycle States

Alerts progress monotonically through the following forward-only lifecycle:

```text
       ┌──────────────┐
       │     OPEN     │
       └──────┬───────┘
              │
      acknowledge()
              ▼
    ┌──────────────────┐
    │   ACKNOWLEDGED   │
    └─────────┬────────┘
              │
          resolve()
              ▼
       ┌──────────────┐
       │   RESOLVED   │
       └──────────────┘
```

1. **`OPEN`**: Default state upon ingestion from the AI pipeline. Eligible for notification planning and escalation.
2. **`ACKNOWLEDGED`**: Operator has viewed and claimed responsibility for the alert. Escalation timers are cancelled immediately. Idempotent action.
3. **`RESOLVED`**: Investigation complete. Accompanied by a mandatory resolution classification (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `DUPLICATE`, `OTHER`) and optional audited note. Resolving an `OPEN` alert implicitly acknowledges it.

---

## 4. Notification Outbox Terminology

- **`Planner`**: Background scheduler ensuring exactly-once planning of eligible alerts into the notification outbox.
- **`Worker`**: Asynchronous worker claiming due notifications using PostgreSQL `FOR UPDATE SKIP LOCKED` leases.
- **`Escalation`**: Automatic secondary notification dispatched to supervisors when a `CRITICAL` alert remains `OPEN` beyond a configurable timeout (default 300 s).
- **`Digest`**: Grouped summary email consolidating multiple alerts within a sliding time window (default 600 s) to prevent inbox fatigue.
- **`Cooldown`**: Throttling period (default 300 s) suppressing repetitive alerts from the same camera and plate/event type. Automatically bypassed if threat priority upgrades.
