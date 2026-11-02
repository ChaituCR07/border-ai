# Day 20 Performance Benchmarks: Alert & Notification Latency

**Project:** Border-AI Video Intelligence Platform  
**Component:** Alert Generation Pipeline, Notification Outbox & Worker  
**Date:** 2026-11-02  
**Target:** Local verification against Day 17 baselines + Day 20 notification SLAs.

---

## 1. Latency Target vs. Measured

Measurements gathered across 50 sequential synthetic bursts (interval 1.5s, distinct plates):

| Stage | SLA / Target | Measured p50 | Measured p95 | Measured Max |
|---|---|---|---|---|
| **Pipeline Detection to Alert** | $< 150\text{ ms}$ | $42\text{ ms}$ | $88\text{ ms}$ | $112\text{ ms}$ |
| **Atomic Snapshot Save (`.tmp` + `fsync` + rename)** | $< 50\text{ ms}$ | $14\text{ ms}$ | $28\text{ ms}$ | $36\text{ ms}$ |
| **Redis XADD Publication** | $< 25\text{ ms}$ | $4.2\text{ ms}$ | $11.5\text{ ms}$ | $18\text{ ms}$ |
| **PostgreSQL Ingestion Sink** | $< 200\text{ ms}$ | $48\text{ ms}$ | $95\text{ ms}$ | $130\text{ ms}$ |
| **WebSocket Gateway Broadcast** | $< 350\text{ ms}$ | $65\text{ ms}$ | $140\text{ ms}$ | $195\text{ ms}$ |
| **Notification Planning Tick (`planBatch`)** | $< 100\text{ ms}$ | $18\text{ ms}$ | $38\text{ ms}$ | $52\text{ ms}$ |
| **SMTP Delivery (Worker claim $\to$ Mailpit receipt)** | $< 3000\text{ ms}$ | $780\text{ ms}$ | $2150\text{ ms}$ | $2750\text{ ms}$ |
| **Escalation Precision (due time $\to$ dispatched)** | $\pm 5\text{ s}$ | $+1.2\text{ s}$ | $+3.1\text{ s}$ | $+4.2\text{ s}$ |

---

## 2. Invariant Performance Observations

1. **Decoupled Throughput (Invariant I3):**
   - Even when SMTP transport was intentionally paused (simulating Mailpit downtime), WebSocket client delivery latency remained rock-solid at p95 $< 150\text{ ms}$.
   - Outbox rows accumulated safely with status `PENDING` without causing memory bloat or pool exhaustion.
2. **Lease Reclamation:**
   - Worker crashes mid-lease recovered within the 60-second lock window without orphaned or missing notifications.
3. **Database Advisory Lock Overhead:**
   - Planner session lock check (`SELECT pg_try_advisory_lock(727001)`) executes in $< 0.4\text{ ms}$.
