# Spatial Rules & Analytics Reference Guide (`border-ai`)

## 1. Overview
The Spatial Analytics subsystem evaluates tracked object trajectories against declarative spatial boundaries defined per camera in `configs/zones/<camera_id>.json`. It identifies restricted zone breaches, dwell/loitering behaviors, and virtual tripwire crossings.

---

## 2. Configuration Schema Reference

Rules are defined in `configs/zones/<camera_id>.json`:

```json
{
  "camera_id": "CAM_001",
  "min_track_hits": 3,
  "zones": [
    {
      "id": "Z1",
      "name": "Restricted Zone",
      "type": "restricted",
      "polygon": [[0.10, 0.20], [0.60, 0.20], [0.60, 0.80], [0.10, 0.80]],
      "classes": ["person"],
      "anchor": "bottom_center",
      "min_frames_inside": 3,
      "min_frames_outside": 5,
      "dwell_alert_s": 5.0,
      "loiter_s": 15.0,
      "loiter_max_span": 0.08
    }
  ],
  "lines": [
    {
      "id": "L1",
      "name": "Entry Line",
      "type": "tripwire",
      "p1": [0.0, 0.5],
      "p2": [1.0, 0.5],
      "positive_direction": "IN",
      "classes": ["person"],
      "anchor": "bottom_center",
      "hysteresis": 0.01,
      "cooldown_s": 2.0
    }
  ]
}
```

### Parameter Reference:

| Field | Applies To | Type | Default | Description |
|---|---|---|---|---|
| `camera_id` | Top-level | string | required | Camera ID matching `configs/cameras.json` |
| `min_track_hits` | Top-level | int | `3` | Minimum consecutive detections before evaluating rules |
| `polygon` | Zone | list[[x, y]] | required | Normalized polygon vertices (0.0 to 1.0) |
| `min_frames_inside` | Zone | int | `3` | Consecutive inside frames before firing `ZONE_ENTER` |
| `min_frames_outside` | Zone | int | `5` | Consecutive outside frames before firing `ZONE_EXIT` |
| `dwell_alert_s` | Zone | float | `0.0` | Seconds inside before triggering `ZONE_DWELL` |
| `loiter_s` | Zone | float | `0.0` | Seconds inside before triggering `LOITERING` |
| `loiter_max_span` | Zone | float | `0.08` | Max movement bounding span (fraction of width) for loitering |
| `p1`, `p2` | Line | [x, y] | required | Normalized finite line segment endpoints |
| `positive_direction` | Line | string | `"IN"` | Direction label (`"IN"` or `"OUT"`) for crossing toward the normal side |
| `hysteresis` | Line | float | `0.01` | Half-width of dead band suppressing line-hover jitter |
| `cooldown_s` | Line | float | `2.0` | Suppresses duplicate crossing events for the same track ID |

---

## 3. Line Direction Convention

Because image coordinates place `y = 0` at the top and increase downwards:
- For a line drawn left-to-right (`p1` to `p2`), the normal vector `(-dy, dx)` points **downward**.
- Movement from the negative side to the positive side receives the label assigned to `positive_direction` (default `"IN"`).
- The reverse movement receives the opposite label (`"OUT"`).
- **Arrow Visual Verification:** The visualizer draws an arrow from the line midpoint pointing toward the positive side labeled with `positive_direction`.

---

## 4. Interactive Zone Drawing Tool (`scripts/draw_zones.py`)

To define or adjust spatial boundaries interactively without typing coordinates:

```bash
# GUI interactive mode:
python ai-engine/scripts/draw_zones.py --video datasets/videos/person_walking.mp4 --camera CAM_001

# Headless grid snapshot mode:
python ai-engine/scripts/draw_zones.py --video datasets/videos/person_walking.mp4 --camera CAM_001 --grid
```

### Keybindings:
- `z`: Switch to Zone mode (click vertices, press `Enter` to complete).
- `l`: Switch to Line mode (click two endpoints; auto-completes).
- `u`: Undo last point.
- `d`: Delete last completed shape.
- `s`: Save and validate JSON configuration.
- `q`: Quit.
