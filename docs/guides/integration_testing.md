# Integration Testing Runbook & Guide

This guide describes how to orchestrate, run, and audit the full-system integration test suite for the Border-AI platform.

---

## 1. Prerequisites
- Docker Engine >= 24.0 & Docker Compose v2
- Node.js >= 20.x & npm
- Python >= 3.10
- FFmpeg (for CCTV simulation)

---

## 2. Quickstart: Bringing Up the System

```bash
# 1. Start infrastructure services (Postgres, Redis, MediaMTX, Mailpit) and run migrations
make up

# 2. Inspect system health across all ports and endpoints
make check

# 3. Run the end-to-end smoke test gate
make smoke
```

---

## 3. Running Acceptance Scenarios

To execute deterministic scenario test runs (S0, S1, S2, S3):

```bash
make scenarios
```

Each gating scenario executes 3 consecutive runs and verifies:
- Event and alert type classification
- Threat scoring factor breakdowns
- Exact notification planning
- Time window boundaries
- Zero-loss database reconciliation

---

## 4. Failure Injection & Chaos Testing

To verify pipeline resilience and buffering under infrastructure failure:

```bash
make chaos
```

Simulates Redis drops, Postgres restarts, camera disconnections, and SMTP outages, verifying that no events or alerts are lost.

---

## 5. Privacy & Canary Conformance

To scan logs, artifacts, databases, and payloads for credential leaks or raw biometric vectors:

```bash
make conformance
```

---

## 6. Teardown & Clean Reset

```bash
# Reset all database tables, Redis streams, and test artifacts
make reset

# Stop all containers and terminate lingering streaming processes
make down
```
