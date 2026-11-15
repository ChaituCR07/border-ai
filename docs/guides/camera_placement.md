# Border-AI Camera Placement, Optical Geometry & Site Survey Guide

This guide establishes engineering principles for camera mounting heights, tilt angles, optical focal lengths, and coverage overlaps across perimeter surveillance, restricted yards, and vehicle access gates.

---

## 1. Pixel-Per-Meter (PPM) Engineering Standards

Camera lens selection must adhere to operational PPM density requirements defined by the European Standard EN 62676-4:

| Operational Goal | Minimum PPM Required | Visual Resolution | Target Applications |
|---|---|---|---|
| **Perimeter Detection (YOLOv8)** | **25 – 40 PPM** | Target occupies $\ge 32$ vertical pixels | Remote boundary line crossings, open fields |
| **Track Classification** | **60 – 100 PPM** | Discern person vs animal vs vehicle | Buffer zone loitering, vehicle lane classification |
| **Recognition & Triage** | **125 – 250 PPM** | Clear clothing, vehicle make/model | Gate approaches, depot entries, security checkpoints |
| **ANPR License Plate OCR** | **$\ge 333$ PPM** | Plate height $\ge 40$ pixels | Dedicated vehicle chokepoints and toll gates |

---

## 2. Perimeter Tripwire & Spatial Zone Geometry

To maximize the accuracy of the foot-point ground contact tracking engine (ADR 0005):

```
              Pole Mount (3.5m - 5.0m)
                     [CAM]
                       │ \
                       │   \
                       │     \  Optimal Pitch: 15° - 25°
                       │       \
      Ground Plane     ▼─────────\──────────► Target Foot-Point (Ground Contact)
                     Dead Zone   Perimeter Line
                     (0 - 4m)     (10m - 25m)
```

1. **Mounting Elevation:**
   - Mount perimeter pole cameras between **$3.5\,\text{m}$ and $5.0\,\text{m}$** above the ground plane.
   - Low mounting heights ($<2.5\,\text{m}$) cause targets to occlude each other in crowded walkways.
   - Excessive mounting heights ($>7.0\,\text{m}$) compress the ground plane perspective and obscure upright target silhouettes.
2. **Camera Tilt / Pitch ($\theta_{\text{pitch}} \in [15^\circ, 25^\circ]$):**
   - A moderate downward angle ensures the bottom edge of the person's bounding box lands squarely on the ground plane, enabling precise polygon containment testing.
3. **Tripwire Orientation:**
   - Draw virtual tripwires perpendicular to the primary expected pedestrian or vehicle travel vectors. Avoid lines drawn parallel to the optical camera line of sight.

---

## 3. Cross-Camera Topology Overlap Guidelines

For seamless cross-camera vehicle journey reconstruction (`CAM-01` $\to$ `CAM-02` $\to$ `CAM-04`):
1. **Field of View (FOV) Overlap:**
   - Adjacent camera nodes should share a **$10\% - 15\%$ visual overlap** or be separated by well-defined transition corridors.
2. **Topology Transition Bounds (`configs/topology.json`):**
   - Measure physical road distance $D$ between adjacent cameras.
   - For an average site speed limit $V_{\text{avg}}$ (e.g. $20\,\text{km/h}$):
     $$T_{\text{expected}} = \frac{D}{V_{\text{avg}}}$$
     $$T_{\text{min}} = \frac{D}{V_{\text{max}}} \quad (\text{e.g. at } 40\,\text{km/h})$$
     $$T_{\text{max}} = 3 \times T_{\text{expected}}$$
   - Any transit faster than $T_{\text{min}}$ triggers an `IMPOSSIBLE_SPEED` alert flag.

---

## 4. ANPR Chokepoint Installation

For license plate capture, refer to the dedicated [ANPR Optical Guidance](anpr_camera_guidance.md):
- Keep horizontal yaw angle $\theta_{\text{yaw}} \le 30^\circ$ relative to lane centerline.
- Enforce shutter speeds of **$1/1000\,\text{s}$** to eliminate vehicle motion blur.
- Utilize active $850\,\text{nm}$ infrared illumination to mitigate headlight flare.
