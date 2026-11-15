#!/usr/bin/env python3
"""
gen_adr_index.py - Automatically scans docs/decisions/*.md and generates
the official Architecture Decision Record (ADR) index at docs/decisions/README.md.
"""

import glob
import os
import re
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DECISIONS_DIR = os.path.join(ROOT_DIR, "docs", "decisions")
OUTPUT_INDEX = os.path.join(DECISIONS_DIR, "README.md")

TEN_SHAPING_DECISIONS = """## Ten Architecture Decisions that Shaped Border-AI

1. **Foot-Point Ground Contact for Spatial Tripwires ([ADR 0005](0005-zone-tripwire-semantics-hysteresis.md)):** Anchoring spatial zone and line crossing checks to the bottom-center foot coordinate of bounding boxes eliminated false triggers caused by torso sway, camera angle pitch, and upper-body projections.
2. **Track-Level Aggregation & Summaries ([ADR 0013](0013-storage-tiering-and-track-level-aggregation.md)):** Persisting structured track life summaries instead of raw per-frame bounding boxes reduced relational storage volume by 99.5% while preserving forensic fidelity.
3. **Local Journal + Redis Streams + Idempotent Postgres ([ADR 0014](0014-polyglot-pipeline-data-ownership.md)):** A local append-only journal in the AI engine ensures zero telemetry loss during transient network partitions, flushing seamlessly via Redis Streams to idempotent PostgreSQL sinks upon recovery.
4. **WebSocket Notifications with REST Keyset Resync ([ADR 0020](0020-websocket-alert-protocol.md)):** Real-time alerting over WebSockets notifies operators within 50ms, while the database remains the immutable source of truth, backed by $O(1)$ cursor-paginated REST endpoints.
5. **Transactional Database Outbox for Notifications ([ADR 0029](0029-transactional-outbox-email-delivery.md)):** Anti-join transactional outbox polling guarantees reliable, at-least-once external SMTP email dispatch without distributed transaction overhead.
6. **Keyset Pagination with Microsecond Timestamps ([ADR 0015](0015-keyset-pagination-for-events.md)):** Stable `(timestamp DESC, event_id DESC)` cursor pagination guarantees zero row skipping or duplicate entries when navigating fast-moving real-time CCTV event streams.
7. **Phonetic & Look-Alike Watchlist Matrix ([ADR 0023](0023-ocr-lookalike-classes-and-levenshtein.md)):** Modeling character substitution costs (`B/8`, `O/0`, `1/I`, `S/5`) enables high-recall vehicle watchlist matching despite environmental camera blur and glare.
8. **Explainable Multi-Camera Topology Plausibility ([ADR 0026](0026-multi-camera-topology-correlation.md)):** Reconstructing vehicle journeys across cameras using configured transition bounds, speed plausibility, and anomaly penalties (impossible speed flag) surfaces reliable suspect timelines.
9. **Event Reconciliation as System Correctness Oracle ([ADR 0034](0034-e2e-event-reconciliation-harness.md)):** Automated reconciliation harnesses verify mathematical invariants between video truth, AI engine detections, streaming queues, and database records.
10. **Deny-by-Default RBAC & Secret Isolation ([ADR 0048](0048-least-privilege-rbac-and-security-hardening.md), [ADR 0050](0050-deployment-topology-networks-run-modes.md)):** Strict non-root execution, 3-tier internal network segmentation, zero plaintext secrets in images, and file-based runtime secrets prevent privilege escalation and lateral movement.
"""

def extract_adr_metadata(file_path):
    rel_name = os.path.basename(file_path)
    match = re.match(r"^(\d{4})-(.*)\.md$", rel_name)
    if not match:
        return None
        
    adr_num = match.group(1)
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Title extraction
    title_match = re.search(r"^#\s+(?:ADR\s+\d+:\s*)?(.*)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else match.group(2).replace("-", " ").title()

    # Status extraction
    status_match = re.search(r"##\s+Status\s*\n+([^\n]+)", content, re.IGNORECASE)
    status = status_match.group(1).strip() if status_match else "Accepted"

    # Context / Decision summary extraction
    dec_match = re.search(r"##\s+Decision\s*\n+([^\n]+)", content, re.IGNORECASE)
    if dec_match:
        summary = dec_match.group(1).strip()
        summary = re.sub(r"^[0-9\.\-\*\s]+", "", summary)
    else:
        summary = title

    if len(summary) > 90:
        summary = summary[:87] + "..."

    return {
        "num": adr_num,
        "filename": rel_name,
        "title": title,
        "status": status,
        "summary": summary
    }

def generate_index():
    adr_files = sorted(glob.glob(os.path.join(DECISIONS_DIR, "????-*.md")))
    records = []
    for f in adr_files:
        meta = extract_adr_metadata(f)
        if meta:
            records.append(meta)

    lines = [
        "# Border-AI Architecture Decision Records (ADRs)",
        "",
        "This directory logs the architectural, design, operational, and security decisions that govern the Border-AI Video Intelligence Platform across its 28-day lifecycle.",
        "",
        TEN_SHAPING_DECISIONS,
        "---",
        "",
        "## Complete Architecture Decision Log",
        "",
        "| ADR | Title | Status | Primary Decision / Architectural Impact |",
        "|---|---|---|---|"
    ]

    for r in records:
        link = f"[{r['num']} - {r['title']}]({r['filename']})"
        lines.append(f"| **{r['num']}** | {link} | `{r['status']}` | {r['summary']} |")

    lines.append("")
    output_text = "\n".join(lines)

    with open(OUTPUT_INDEX, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"[OK] Generated ADR index with {len(records)} records at: {OUTPUT_INDEX}")
    return True

if __name__ == "__main__":
    generate_index()
