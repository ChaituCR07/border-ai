# Field Recording Guide for False-Positive and Boundary Testing

**Project:** Border-AI Video Intelligence Platform  
**Target:** Standardized collection of controlled false-positive and true-positive test footage  

---

## 1. Camera Setup and Technical Specifications

To ensure reproducible testing across detection, tracking, ANPR, and rule evaluation layers, all test footage must adhere to the following setup parameters:

- **Mounting:** Rigid tripod mount with pan-tilt head locked. No handheld capture.
- **Resolution:** Standard $1280 \times 720$ (720p) or $1920 \times 1080$ (1080p).
- **Framerate:** Constant $25.0\,\text{FPS}$ or $30.0\,\text{FPS}$ (no variable framerate VFR).
- **Encoding:** H.264 / MP4 with baseline/main profile, keyframe interval (GOP) $\le 2.0\,\text{s}$.
- **Lighting:** Record explicit daylight (overcast and direct sun), twilight/dusk, and night IR scenes.
- **Take Duration:** 20 to 60 seconds per controlled scenario. Negative long-exposure takes: 10 to 30 minutes.

---

## 2. Slate and Take Identifier Protocol

Each recording must begin with a 2-second visual or audio slate:
- Visual slate: A handheld card or digital display showing `[SCENARIO-ID] | [CAM-ID] | [DATE] | [TAKE-NUM]`.
- Naming convention: `footage/fp/<category>/<scenario_id>_take<nn>.mp4`.
- Log entries must be entered into `footage/MANIFEST.md` immediately following capture.

---

## 3. Controlled Scenario Recording Catalog

### 3.1 Person and Zone Scenarios (Plan Tests 1 & 2)

| Take ID | Scene Type | Action Description | Expected Rule Behavior |
|---|---|---|---|
| `FP-1.1` | Negative Control | Person walking parallel to zone boundary, $\ge 150\,\text{px}$ outside. | No zone entry, no alert. |
| `FP-1.2` | Negative Control | Person walking along boundary within $20\text{--}50\,\text{px}$ outside for 60s. | No zone entry (tests hysteresis). |
| `FP-1.3` | Perspective Stress | Person standing with upper body leaning over boundary; feet outside. | No zone entry (tests foot-point semantics). |
| `FP-1.4` | Jitter Stress | Person standing stationary $10\,\text{px}$ outside boundary for 120s. | No enter/exit flicker. |
| `FP-1.5` | Occlusion Recovery| Person walks behind pole outside boundary and emerges outside. | Track reacquired, no zone entry. |
| `FP-1.6` | Group Outside | Group of 3-5 persons congregating outside boundary. | No zone event. |
| `FP-1.7` | Non-Person Objects| Backpack, cardboard cutout, or bicycle placed inside/outside zone. | No person alert. |
| `TP-2.1` | Positive Control | Direct perpendicular entry through boundary to depth $\ge 100\,\text{px}$. | Exactly 1 `ZONE_ENTER` alert within $500\,\text{ms}$. |
| `TP-2.2` | Oblique Entry | Person enters at shallow angle ($30^\circ$) across boundary. | Single `ZONE_ENTER` alert. |
| `TP-2.3` | Fast Entry | Person running across boundary ($>250\,\text{px/s}$). | Rapid `ZONE_ENTER` alert before exit. |
| `TP-2.4` | Low-Light Entry | Person entering under low illumination / night IR. | Single `ZONE_ENTER` alert. |
| `TP-2.5` | Occluded Entry | Person enters zone behind foreground obstacle. | Single `ZONE_ENTER` alert upon reacquisition. |

### 3.2 Vehicle and Line Scenarios (Plan Tests 5 & 6)

| Take ID | Scene Type | Action Description | Expected Rule Behavior |
|---|---|---|---|
| `FP-5.1` | Permitted Flow | Continuous stream of vehicles crossing in permitted direction. | Normal count increment, 0 violations. |
| `FP-5.2` | Stop-and-Go | Vehicle stops directly straddling counting line, then proceeds. | Single crossing, 0 wrong-way alerts. |
| `FP-5.3` | Oblique Crossing | Vehicle crosses counting line at $45^\circ$ angle. | Single permitted crossing. |
| `FP-5.4` | Line Occlusion | Two vehicles cross simultaneously side-by-side. | Two independent counts, 0 false wrong-ways. |
| `FP-5.5` | Stationary Line | Vehicle parked over counting line for 30 seconds. | 0 additional crossing events after initial. |
| `TP-6.1` | Wrong-Way Flow | Vehicle drives against permitted direction across line. | Immediate `LINE_CROSSING_WRONG_DIRECTION`. |
| `TP-6.2` | Oblique Reverse | Vehicle reverses diagonally across line. | Single wrong-way direction alert. |

### 3.3 License Plate Scenarios (Plan Tests 3 & 4)

| Take ID | Scene Type | Action Description | Expected Rule Behavior |
|---|---|---|---|
| `FP-3.1` | Normal Plates | Unlisted vehicles passing ANPR camera (100-plate list active). | Reads logged, 0 watchlist alerts. |
| `FP-3.2` | Near-Miss Plate | Plate differing by 1 character from watchlist entry (e.g. `B` vs `8`). | Look-alike gating applied, no CRITICAL alert. |
| `FP-3.3` | Partial Read | Obscured plate or low-confidence read ($<0.70$). | Filtered by confidence threshold. |
| `TP-4.1` | Watchlisted Vehicle| Vehicle on active watchlist passes camera. | Single `WATCHLIST_HIT` alert ($90/CRITICAL$). |
| `TP-4.2` | Low-Light Watchlist| Watchlisted vehicle under night illumination. | Plate OCR consensus match, alert triggered. |

---

## 4. Privacy and Evidence Export Standards

1. **Plate Auto-Blurring:** All extracted evidence clips or debug visualizations containing license plates of third-party public vehicles must be blurred prior to team sharing or commit.
2. **Local Storage:** Raw captured footage must reside in `footage/` or local external storage. Do not commit heavy video files to git.
3. **Synthetic Overlays:** For testing near-miss watchlist plates where physical vehicle plates are unavailable, use the synthetic overlay generator and document the overlay flag in `footage/MANIFEST.md`.
