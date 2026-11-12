# Controlled False-Positive & True-Positive Test Catalog

**Project:** Border-AI Video Intelligence Platform  
**Specification:** Six Plan Test Pairs and System-Tier Variants  
**Associated ADRs:** ADR 0044, ADR 0045, ADR 0046  

---

## 1. Test Pairs Summary

| Plan Test Pair | Negative Spec (Expected: NO ALERT) | Positive Spec (Expected: ALERT) |
|---|---|---|
| **Pair 1 / 2 (Person Zone)** | **Test 1:** Person outside restricted zone | **Test 2:** Person enters restricted zone |
| **Pair 3 / 4 (Plate Watchlist)** | **Test 3:** Vehicle with normal plate | **Test 4:** Watchlisted plate |
| **Pair 5 / 6 (Vehicle Line)** | **Test 5:** Vehicle crosses in permitted direction | **Test 6:** Vehicle crosses in wrong direction |

---

## 2. Exhaustive Scenario Matrix

### 2.1 Test 1 (Negative) & Test 2 (Positive): Person / Restricted Zone

| Spec ID | Type | Scenario Description | Expected Outcome | Forbidden Events | Status |
|---|---|---|---|---|---|
| `FP-1.1` | Neg | Person walks parallel $\ge 150\,\text{px}$ outside zone | No zone event, 0 alerts | Any alert $\ge\text{MEDIUM}$ | PASS |
| `FP-1.2` | Neg | Person walks along boundary within $20\text{--}50\,\text{px}$ outside | 0 zone events | `RESTRICTED_ZONE_ENTRY` | PASS |
| `FP-1.3` | Neg | **Perspective overlap:** Head/torso in zone, feet strictly outside | 0 zone events (foot-point semantics) | `RESTRICTED_ZONE_ENTRY` | PASS |
| `FP-1.4` | Neg | Person stationary $10\,\text{px}$ outside boundary for 120s | 0 enter/exit flicker events | Multiple `ZONE_ENTER` | PASS |
| `FP-1.5` | Neg | Person temporarily occluded behind pole outside boundary | Track re-acquired, 0 zone events | `RESTRICTED_ZONE_ENTRY` | PASS |
| `FP-1.6` | Neg | Group of 5 people walking together outside boundary | 0 zone events | Any alert | PASS |
| `FP-1.7` | Neg | Non-person objects (backpack, bike, animal) placed near zone | 0 person events | Person `RESTRICTED_ZONE_ENTRY` | PASS |
| `TP-2.1` | Pos | Clear direct perpendicular entry deep into zone | 1 alert within $500\,\text{ms}$ ($60/\text{HIGH}$) | Missed alert | PASS |
| `TP-2.2` | Pos | Oblique entry at $30^\circ$ angle | 1 alert within $750\,\text{ms}$ | Missed alert | PASS |
| `TP-2.3` | Pos | Rapid sprinting entry ($>250\,\text{px/s}$) | 1 alert before zone exit | Missed alert | PASS |
| `TP-2.4` | Pos | Night IR low-contrast entry | 1 alert ($60/\text{HIGH}$) | Missed alert | PASS |
| `TP-2.5` | Pos | Entry with partial occlusion at boundary | 1 alert upon reacquisition | Missed alert | PASS |
| `TP-2.6` | Pos | Two persons enter zone simultaneously | Episode aggregation: 1 alert | Zero alerts | PASS |

### 2.2 Test 3 (Negative) & Test 4 (Positive): ANPR Watchlist

| Spec ID | Type | Scenario Description | Expected Outcome | Forbidden Events | Status |
|---|---|---|---|---|---|
| `FP-3.1` | Neg | 100 normal vehicles with unlisted license plates | Reads recorded, 0 watchlist alerts | Any watchlist alert | PASS |
| `FP-3.2` | Neg | Near-miss plate (1 character differing, e.g. `B` vs `8`) | Look-alike policy gating applied | False $\text{CRITICAL}$ alert | PASS |
| `FP-3.3` | Neg | Low-confidence read ($<0.70$) or motion-blurred plate | Read discarded or marked unverified | Watchlist alert | PASS |
| `FP-3.4` | Neg | Two-wheeler motorcycle two-line plate (non-watchlisted) | OCR read or skipped | False match alert | PASS |
| `TP-4.1` | Pos | Watchlisted vehicle in clear daylight | 1 alert ($90/\text{CRITICAL}$) within $400\,\text{ms}$ | Missed alert | PASS |
| `TP-4.2` | Pos | Watchlisted vehicle in night IR lighting | 1 alert ($90/\text{CRITICAL}$) | Missed alert | PASS |
| `TP-4.3` | Pos | Watchlisted plate partially occluded across 3 frames | Consensus filter matches plate | Missed alert | PASS |
| `TP-4.4` | Pos | Watchlist plate with OCR look-alike character | Corroborated match produces alert | Missed alert | PASS |
| `LIM-4.5` | Lim | Plate below usable height ($<20\,\text{px}$) | **Documented limitation:** no alert | – | OUT_OF_SCOPE |

### 2.3 Test 5 (Negative) & Test 6 (Positive): Vehicle Counting & Direction

| Spec ID | Type | Scenario Description | Expected Outcome | Forbidden Events | Status |
|---|---|---|---|---|---|
| `FP-5.1` | Neg | High-volume traffic crossing in permitted direction | Count increments, 0 violations | Any `LINE_CROSSING_WRONG_DIRECTION` | PASS |
| `FP-5.2` | Neg | Stop-and-go vehicle stopping directly over counting line | Exactly 1 crossing count, 0 violations | Repeated crossing alerts | PASS |
| `FP-5.3` | Neg | Oblique crossing across line ($45^\circ$) | 1 permitted crossing, 0 violations | Direction violation | PASS |
| `FP-5.4` | Neg | Two vehicles crossing side-by-side with ID switch | 2 counts, dedupe prevents reverse event | False wrong-way event | PASS |
| `FP-5.5` | Neg | Vehicle parked over line for 60 seconds | 0 additional crossings after initial | Oscillating crossing events | PASS |
| `FP-5.6` | Neg | Pedestrian walking across vehicle counting line | Class filter suppresses line event | Any vehicle line event | PASS |
| `TP-6.1` | Pos | Vehicle driving wrong-way across counting line | Immediate `LINE_CROSSING_WRONG_DIRECTION` | Missed violation | PASS |
| `TP-6.2` | Pos | Oblique wrong-way reversal | 1 wrong-way violation | Missed violation | PASS |
| `TP-6.3` | Pos | Slow wrong-way reverse ($10\,\text{px/s}$) | 1 wrong-way violation | Missed violation | PASS |
| `TP-6.4` | Pos | Wrong-way vehicle among dense permitted flow | 1 wrong-way violation isolated | Missed violation | PASS |

### 2.4 Control Scenarios (Negative Baselines)

| Spec ID | Type | Scenario Description | Expected Outcome | Forbidden Events | Status |
|---|---|---|---|---|---|
| `FP-X.1` | Neg | Empty static scene (15 minutes exposure) | 0 events, 0 alerts | Any event | PASS |
| `FP-X.2` | Neg | Normal activity during after-hours clock window | Max alert tier: $\text{LOW}$ (score +10) | Alert $\ge\text{MEDIUM}$ | PASS |
| `FP-X.3` | Neg | Multiple weak signals (after-hours + permitted line) | Max alert tier: $\text{LOW}$ (score +20) | Alert $\ge\text{MEDIUM}$ | PASS |
