# Forensic Investigation Guide

## Overview

The Border AI Investigation Dashboard (`/investigation`) is a forensic workbench designed for retrospective incident analysis, vehicle movement tracing, temporal correlation, and evidence export.

---

## 1. Search Semantics & Omnibox Syntax

The investigation search interface provides both structured query tokens and intelligent free-text classification.

### 1.1 Supported Structured Tokens

| Token | Example | Description |
|---|---|---|
| `cam:` or `camera:` | `cam:CAM-01,CAM-03` | Filter by one or multiple cameras. |
| `type:` | `type:RESTRICTED_ZONE_ENTRY` | Filter by event classification type. |
| `sev:` or `severity:` | `sev:CRITICAL,HIGH` | Filter by alert severity. |
| `score:` | `score:>75` or `score:80-100` | Filter by 0–100 threat score range. |
| `plate:` | `plate:KA01AB1234` or `plate:KA01*` | Query license plate (exact, look-alike, prefix, or contains). |
| `vehicle:` or `veh:` | `vehicle:VEH-1002` | Filter by tracked vehicle identifier. |
| `person:` or `per:` | `person:PER-401` | Query person identifier (Investigator role + purpose required). |

### 1.2 Free-Text Auto-Classification

Typing untagged text into the Omnibox triggers automatic heuristics:
- **UUIDs** (e.g. `11111111-2222-3333-4444-555555555555`) $\to$ Direct event selection.
- **Plate patterns** (e.g. `KA01AB1234`, `MH12CD5678`) $\to$ Look-alike plate search.
- **Free words** (e.g. `intruder near fence`) $\to$ Full-text keyword search (`q`).

### 1.3 Confusable OCR Matching (Look-Alike Mode)

ANPR cameras frequently misrecognize visually similar characters (e.g., `0` vs `O`, `1` vs `I`, `8` vs `B`). In **Look-alike** mode (the default), character substitutions are resolved symmetrically using a shared canonical key (`plate_key`):

$$\{O, Q, D\} \leftrightarrow 0, \quad \{I, L\} \leftrightarrow 1, \quad Z \leftrightarrow 2, \quad A \leftrightarrow 4, \quad S \leftrightarrow 5, \quad G \leftrightarrow 6, \quad T \leftrightarrow 7, \quad B \leftrightarrow 8$$

Events matching via OCR look-alike substitution are visibly badged with an amber **Look-alike** pill in results.

---

## 2. Temporal & Disjunctive Filtering

- **Time Range Presets:** Quick filter buttons for **Last 1h**, **Last 24h**, and **Last 7d**.
- **Time-of-Day Window:** Allows filtering events within specific daily hours (e.g., `22:00` to `05:00`). Windows that wrap midnight are evaluated disjunctively.
- **Disjunctive Facets:** Selecting a camera (e.g. `CAM-01`) recalculates total counts while keeping other camera facet counts visible, preventing zero-count collapse.

---

## 3. Vehicle Journey Reconstruction

Entering a plate or clicking the **Journey** button reconstructs the chronological route taken by the vehicle:
- **Camera Sightings:** Consecutive detections on the same camera within 120 seconds are automatically collapsed into a single `Sighting` card showing first seen, last seen, event count, and peak threat score.
- **Transition Gap Arrows:** Indicates elapsed travel time in seconds between consecutive cameras (e.g. `+28s`, `+72s`).
- **OCR Variants Banner:** Alerts analysts if multiple plate variations were captured across sightings (e.g., `KA01AB1234` and `KA0IAB1234`).
- **Interactive Deep Links:** Clicking any sighting card immediately focuses the table on that camera and temporal window.

---

## 4. Privacy & Audit Compliance

1. **Role Gating:**
   - Operators can search general event telemetry and filter by camera, time, and severity.
   - Person-identifier lookups, bulk CSV exports, and vehicle journey reconstructions are restricted to **Investigator** and **Admin** roles.
2. **Explicit Purpose Mandate:**
   - Person searches and CSV exports require an explicit investigative purpose string ($\ge 5$ characters).
   - Missing purpose returns HTTP 422 `PURPOSE_REQUIRED`.
3. **Immutable Audit Trail:**
   - Every sensitive search (plate, vehicle, person) and every export action is recorded to `api_audit_log` with user ID, role, IP address, timestamp, full query payload, and stated purpose.
4. **Formula Injection Protection:**
   - Exported CSV files process all cell values through formula neutralization (`csvCell`), prepending single quotes (`'`) to cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r`.
