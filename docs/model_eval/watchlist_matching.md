# Watchlist Collision Modeling & False Match Policy

**Evaluation Reference:** ADR 0023, ADR 0039  
**Run ID:** `run-20261105-watchlist-sim`  
**Date:** 2026-11-05  

---

## 1. Context & Matching Semantics

In border surveillance and access control, vehicle license plates are screened against active security watchlists (e.g. stolen vehicles, contraband transport, amber alerts). Under ADR 0023, BorderVision supports two matching modalities:
1. **Exact Matching:** `pred_plate == watchlist_plate`
2. **Look-Alike Matching:** `plate_key(pred_plate) == plate_key(watchlist_plate)`

While look-alike matching prevents vehicles from escaping detection due to optical character recognition noise (such as `0` recognized as `O` or `8` as `B`), expanding the equivalence space introduces a risk of **false-positive collisions** against benign passing traffic.

---

## 2. Collision Probability Simulation

Simulated across a background traffic pool of 20,000 distinct Indian registration plates:

| Watchlist Size ($W$) | Match Modality | Collision Probability / Veh | Expansion Ratio | Low Traffic (1k veh/day) | Med Traffic (10k veh/day) | High Traffic (50k veh/day) |
|---|---|---|---|---|---|---|
| **$W = 10$** | Exact | $5.0 \times 10^{-4}$ | $1.0\times$ | $0.50$ / day | $5.0$ / day | $25.0$ / day |
| **$W = 10$** | Look-Alike | $8.2 \times 10^{-4}$ | $1.64\times$ | $0.82$ / day | $8.2$ / day | $41.0$ / day |
| **$W = 100$** | Exact | $5.0 \times 10^{-3}$ | $1.0\times$ | $5.0$ / day | $50.0$ / day | $250.0$ / day |
| **$W = 100$** | Look-Alike | $8.2 \times 10^{-3}$ | $1.64\times$ | $8.2$ / day | $82.0$ / day | $410.0$ / day |
| **$W = 1,000$** | Exact | $5.0 \times 10^{-2}$ | $1.0\times$ | $50.0$ / day | $500.0$ / day | $2,500.0$ / day |
| **$W = 1,000$** | Look-Alike | $8.2 \times 10^{-2}$ | $1.64\times$ | $82.0$ / day | $820.0$ / day | $4,100.0$ / day |
| **$W = 10,000$** | Exact | $5.0 \times 10^{-1}$ | $1.0\times$ | $500.0$ / day | $5,000.0$ / day | $25,000.0$ / day |
| **$W = 10,000$** | Look-Alike | $8.2 \times 10^{-1}$ | $1.64\times$ | $820.0$ / day | $8,200.0$ / day | $41,000.0$ / day |

---

## 3. Operational Policy Decisions (ADR 0039)

The simulation shows that at large watchlist sizes ($W \ge 1,000$), uncorroborated look-alike matching produces unsustainable false alert volumes ($>800$ alerts/day on medium-traffic lanes).

To preserve high sensitivity without operator alert fatigue, BorderVision enforces the following alert policies:

1. **Exact Matches:**
   - Immediately dispatches high-priority **CRITICAL** alert.
   - Triggers automated gate interlock or barrier hold (where configured).
   - Contributes full $1.0$ weight to vehicle threat score.

2. **Look-Alike Only Matches:**
   - **Corroborated Requirement:** Dispatches an active security alert **only if** supported by multi-frame consensus stability ($\ge 3$ agreeing reads, or confidence $\ge 0.85$).
   - **Visual Tagging:** Marked with a prominent amber `[Look-Alike Equivalent]` badge in the operator dashboard, displaying both the detected string and the matched watchlist key.
   - **Single-Frame Transient Hits:** Filtered out as advisory background events, preventing false alarm fatigue.
