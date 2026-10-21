# 0011. Threat Scoring Engine Architecture and Semantics

**Date:** 2026-10-21  
**Status:** Accepted  
**Deciders:** Core Engineering Team  
**Consulted:** Video Analytics & Threat Assessment Stakeholders  

---

## Context

In Day 11, we delivered the configurable Behaviour Analysis Engine capable of raising high-level compound events (`ZONE_VIOLATION`, `DIRECTION_VIOLATION`, `LOITERING_VIOLATION`, `AFTER_HOURS_ACTIVITY`, `UNAUTHORIZED_VEHICLE_AFTER_HOURS`). However, standalone alerts present an overwhelming operational cognitive load without an aggregate, explainable threat metric.

Day 12 introduces the Threat Scoring Engine (`ThreatScorer`), combining geometric analytics (line crossings, zone entries), identity checks (watchlist hits), and behavioural events into an explainable 0–100 threat score and 4-tier alert level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).

---

## Decisions

### 1. Score the Entity, Not the Event
The scoring unit is an **Entity**: a tracked physical object, or (when an ANPR plate is recognized) the **vehicle identified by that plate**. Tracks that swap IDs or fragment across occlusions are unified when they share a recognized plate (`merge_by_plate: true`), preventing threat score resets on tracker errors.

### 2. Evidence Expires Within a Sliding Window
Threat contributions are valid only within a configurable sliding time window (`window_s: 600`, 10 minutes). Stale observations from hours ago decay naturally. Repeating the same evidence within the window updates the timestamp and refreshes its validity without artificially compounding points.

### 3. Count Each Kind of Evidence Once by Default
To prevent jitter or repeated crossings from runaway point accumulation, each source kind is counted at most `max_occurrences: 1` times (unless explicitly configured higher, such as multi-line crossings). When multiple occurrences occur, the highest-scoring/most-recent is preserved.

### 4. No Double Counting of the Same Physical Fact
A wrong-way crossing is simultaneously a physical line crossing (+20) and an unauthorized direction violation (+20). The scoring configuration specifies `excluded_by: ["direction_violation"]` on the `line_crossing` source. When a direction violation is present, the raw crossing is excluded, ensuring accurate 100-point scoring for Scenario 2.

### 5. Multi-Suspicious Event Bonus Requires Four Distinct Kinds
The platform awards a +10 bonus when multiple distinct suspicious indicators are observed. To align with Plan Scenario 1 (which scores exactly 60 with 3 events: line crossing + restricted zone + after hours), the bonus threshold `min_distinct_kinds` is calibrated to **4**.

### 6. Review-Grade Evidence Receives Half Weight
Unconfirmed watchlist hits (e.g. fuzzy/near license plate matches, review-status facial candidates) are assigned a `status_multiplier` of `0.5`, requiring human triage while still elevating situational awareness.

### 7. Alerts Follow Strict Escalation
To prevent alert fatigue, alerts are raised only when:
- An entity first crosses `alert_min_score` (default 10).
- The threat level **rises** above the entity’s previous high-water mark (e.g. `MEDIUM` -> `HIGH`).
- A de-escalation must persist for `rearm_s` (300s) before a new episode can re-alert, subject to an inter-episode `cooldown_s` (60s).

### 8. Explainable Alerts
Every `THREAT_ALERT` carries a transparent audit trail:
- Final score (`threat_score`) and level (`severity`/`priority`).
- Plain-language summary string.
- Itemized list of contributions: source event ID, label, points added, timestamp, and triggering reasons.
- Excluded items and applied bonuses.

### 9. Decoupling Scoring from Downstream Action
The scorer produces deterministic scores, priorities, and alert events. Notification routing, Redis Streams transport (Day 13), database persistence (Day 14), and operator acknowledgement workflows remain strictly decoupled.

### 10. Privacy and Evidence Snapshots
Evidence frames (`snapshots/<alert_id>.jpg`) contain unredacted imagery. They are persisted exclusively in `outputs/runs/<run_id>/snapshots/` (ignored by version control) and can be toggled off via `--no-snapshots`.

---

## Reconciliation of Plan Discrepancies

- **Section 5 Illustration (78 vs 55):** Section 5 of the design document illustrated a score of 78 for restricted zone + after hours + unknown person + loitering. In the formal weights table, no weight is defined for "unknown person". With the table weights: 30 (zone) + 10 (after-hours) + 15 (loitering) = 55 (`MEDIUM`). The engine strictly adheres to the formal specification table. If an operator requires an "unknown person" weight, it can be added purely via JSON configuration without code changes.

---

## Consequences

- **Positive:** Deterministic, fully testable threat arithmetic; seamless track-stitching by plate; zero alert spam on steady-state threats; complete operator explainability.
- **Trade-offs:** Single-camera person tracking cannot survive prolonged tracker ID resets without Re-ID (deferred to later milestones).
