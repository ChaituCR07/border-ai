# Platform Configuration (`configs`)

The `configs/` directory stores declarative configuration files defining AI detection thresholds, camera streams, and spatial security polygons. Decoupling configuration from application code allows dynamic adjustment of camera parameters and security boundaries without restarting core services.

---

## 1. Directory Structure

```text
configs/
├── app.yaml                   # Global AI model, confidence, and tracker settings
├── cameras.json               # Camera inventory, stream URLs, and target frame rates
├── rules.json                 # Threat scoring weights and alert thresholds (Week 2)
└── zones/
    └── CAM_001.json           # Per-camera normalized spatial polygons & virtual tripwires
```

---

## 2. Configuration Files & Schemas

### 2.1 `app.yaml` — AI Model & Tracker Configuration
Configures inference models, detection confidence thresholds, and multi-object tracking buffers.
```yaml
model:
  name: yolov8n.pt              # YOLO model weights (yolov8n, yolov8s, etc.)
  device: auto                  # auto | cpu | cuda:0 | mps
  confidence: 0.4               # Minimum confidence threshold for valid detection
  iou: 0.5                      # Non-Maximum Suppression (NMS) IoU threshold
  image_size: 640               # Model input resolution
  classes: [person, bicycle, car, motorcycle, bus, truck]

tracker:
  type: bytetrack               # Tracking algorithm: bytetrack | botsort
  track_thresh: 0.5             # High score threshold for track continuation
  match_thresh: 0.8             # IoU matching threshold
  track_buffer: 30              # Max frames to keep lost tracks before deletion

video:
  target_fps: 15                # Pipeline inference frame rate
  resize_width: 1280            # Normalized width for consistent inference
```

### 2.2 `cameras.json` — Camera Stream Definitions
Defines all input cameras, their stream sources (file or RTSP), and operational flags.
```json
{
  "cameras": [
    {
      "camera_id": "CAM_001",
      "name": "North Gate",
      "source_type": "file",
      "source": "datasets/videos/person_walking.mp4",
      "target_fps": 15,
      "resize_width": 1280,
      "loop": true,
      "realtime": true,
      "enabled": true
    },
    {
      "camera_id": "CAM_003",
      "name": "South Perimeter (RTSP)",
      "source_type": "rtsp",
      "source": "${RTSP_CAM_003_URL}",
      "target_fps": 15,
      "resize_width": 1280,
      "enabled": true
    }
  ]
}
```
> **Security Note:** Never hardcode camera credentials in `cameras.json`. Use environment variable expansion (e.g. `"${RTSP_CAM_003_URL}"`) and supply credentials in the gitignored `.env` file.

### 2.3 `zones/<CAMERA_ID>.json` — Spatial Boundary Definitions
Defines restricted area polygons and directional virtual tripwires.
```json
{
  "camera_id": "CAM_001",
  "zones": [
    {
      "name": "Restricted Zone",
      "type": "restricted",
      "polygon": [[0.1, 0.2], [0.6, 0.2], [0.6, 0.8], [0.1, 0.8]]
    }
  ],
  "lines": [
    {
      "name": "Entry Line",
      "p1": [0.0, 0.5],
      "p2": [1.0, 0.5],
      "positive_direction": "IN"
    }
  ]
}
```
> **Normalized Coordinates:** Coordinates `[x, y]` are expressed as floating-point ratios between `0.0` and `1.0` relative to frame width and height. This ensures polygons automatically scale correctly regardless of camera resolution changes.
