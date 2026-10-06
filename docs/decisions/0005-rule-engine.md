# 0005: Declarative Spatial Rule Engine & Event Generation

**Status:** Accepted  
**Date:** 2026-10-06  
**Context:** AI Engine Spatial Analytics (`border-ai`)

---

## Decision

We adopt a declarative, state-machine-driven spatial analytics engine decoupled from model inference:
1. **Declarative Rule Schema:** Spatial boundaries are declared in `configs/zones/<camera_id>.json` using normalized (0.0 to 1.0) coordinates, ensuring configurations remain independent of stream resolution changes.
2. **Ground-Contact Anchoring:** All spatial evaluations default to `bottom_center` of the object bounding box (representing ground contact), preventing spurious breaches caused by head height or shadows.
3. **State Machine Event Generation:** Events are generated exclusively from confirmed track state transitions, never directly from raw bounding boxes.
4. **Three-Layer Duplicate Suppression:**
   - *Confirmation Age:* Detections must be tracked for at least `min_track_hits` frames (default: 3) before interacting with rules.
   - *Hysteresis:* Zone boundaries require consecutive frame confirmation (`min_frames_inside: 3`, `min_frames_outside: 5`); virtual lines enforce a dead band (`hysteresis: 0.01` of frame width).
   - *Temporal Cooldown:* Virtual lines enforce a per-track cooldown timer (`cooldown_s: 2.0s`) to prevent duplicate events from lingering or hovering subjects.
5. **Deterministic Cleanup:** Tracks expiring while inside a zone automatically produce a closing `ZONE_EXIT` with `details.reason = "track_ended"`, preserving occupancy counts and preventing orphaned state.

---

## Event Taxonomy

The engine produces 5 standard structured events:
- `ZONE_ENTER`: Confirmed entry across boundary.
- `ZONE_EXIT`: Confirmed departure or track eviction.
- `ZONE_DWELL`: Cumulative presence surpassing threshold (`dwell_alert_s`).
- `LOITERING`: Persistent presence within a localized spatial span (`loiter_max_span`).
- `LINE_CROSSING`: Vector segment intersection with direction (`IN` / `OUT`).

---

## Trade-offs & Limitations Accepted

- **Tracker Identity Coupling:** If multi-object tracking undergoes an ID switch directly on a boundary line, the engine records a new track ID and may fire a secondary entry. Downstream threat scoring (Week 2) mitigates this via spatio-temporal event clustering.
