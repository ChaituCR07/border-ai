# 10. Behaviour Engine (Configurable Rules)

**Date:** 2026-10-19  
**Status:** Accepted  

## Context

The Border-AI platform requires intelligent detection of high-level threat behaviors from raw computer vision observations (detections, tracking, zone presences, line crossings, license plates, watchlist hits, and identity matches). Hardcoding alerts (`if person_in_zone: alert()`) creates brittle, non-reusable logic. We require a configurable, deterministic rule engine that operates purely on facts and observations without touching pixel data.

## Decisions

1. **Observations In, Events Out:** The Behaviour Engine never inspects pixels or raw frames. It consumes existing observations (`ZONE_ENTER`, `LINE_CROSSING`, `PLATE_RECOGNIZED`, `WATCHLIST_MATCH`, etc.) and track state. This decouples analytics from vision models and enables offline fast replay testing without GPU inference.
2. **Rules as Data:** Rules are defined in `configs/rules.json`. Schema mistakes fail at load time with precise rule-level error messages. Rule references to zones or lines are cross-checked against camera zone definitions.
3. **State vs. Event Conditions:** Conditions fall into two categories:
   - *State conditions* (e.g., inside zone for > 60s, time window 22:00-05:00, plate not authorized, track age >= 2s).
   - *Event conditions* (e.g., line crossing with wrong direction within last 5s).
   Rules evaluate the logical `AND` (`all`), `any`, or `not` of conditions.
4. **Fire Once per Episode:** A rule fires when its conditions become newly true for a track and specific binding (zone ID or crossing line), preventing per-frame spam. It can re-arm only after conditions remain false for `rearm_s` seconds, with `cooldown_s` to suppress chatter.
5. **Self-Explaining Events:** Every behaviour event carries `details.reasons` (e.g., `["inside zone Z1 (restricted) for 72 s", "local time 02:13 is within 22:00-05:00"]`), `details.points`, `details.severity`, and `details.bindings`.
6. **Explicit Time and Simulated Clock:** Timezones are configured at the site level with optional per-camera overrides. Evaluation uses local time for window checking. Offline replays support `--clock-start` to evaluate night-time/after-hours rules deterministically.
7. **No Re-ingestion (Loop Prevention):** Behaviour events are tagged with `rule_kind: "behaviour"` and are strictly excluded from ingestion into track contexts.
8. **Safe Hot Reload:** The engine checks modification timestamps on `rules.json`. Valid configurations replace running rules atomically; invalid configurations log an error and retain previous valid rules without disruption.
9. **Fail-Safe Authorization:** Any rule evaluating `plate.authorized` requires a configured `authorized_plates_csv` at load time; otherwise validation fails, preventing unconfigured lists from flagging every vehicle as unauthorized.

## Consequences

- Behaviour detection is fully testable in milliseconds with synthetic scenes and historical event streams.
- Operators can configure site-specific rules without code changes.
- Downstream threat scoring (Day 12) receives structured points and reasons without re-evaluating spatial/temporal rules.
