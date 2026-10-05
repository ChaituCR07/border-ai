# AI Engine REST API Specification (`ai-engine`)

The AI Engine exposes a high-performance REST API on port `8000` for ad-hoc inference, model inspection, and health monitoring.

---

## 1. Endpoints Overview

| Method | Endpoint | Description | Content-Type |
|---|---|---|---|
| `GET` | `/health` | System health, environment, CUDA availability, and model status | `application/json` |
| `GET` | `/model/info` | Active YOLO model architecture, thresholds, classes, and stats | `application/json` |
| `POST` | `/detect` | Upload image, returns structured JSON detections | `multipart/form-data` → `application/json` |
| `POST` | `/detect/annotated` | Upload image, returns annotated JPEG with rendered bounding boxes | `multipart/form-data` → `image/jpeg` |

---

## 2. Request & Response Contracts

### `POST /detect`
Upload an image (`.jpg`, `.png`, etc.) via form-data.

#### Query Parameters:
- `camera_id` (string, optional, default: `"API"`): Camera tag associated with the frame.
- `conf` (float, optional, range: `0.0 - 1.0`): Confidence threshold override.
- `iou` (float, optional, range: `0.0 - 1.0`): NMS IoU threshold override.

#### Example Response:
```json
{
  "camera_id": "CAM_001",
  "frame_id": 0,
  "timestamp": "2026-10-04T16:15:32.481Z",
  "frame_size": {
    "width": 1280,
    "height": 720
  },
  "inference_ms": 14.2,
  "objects": [
    {
      "class": "person",
      "class_id": 0,
      "confidence": 0.912,
      "bbox": [412.3, 188.0, 497.9, 402.6]
    },
    {
      "class": "car",
      "class_id": 2,
      "confidence": 0.874,
      "bbox": [60.1, 300.4, 310.8, 470.2]
    }
  ]
}
```

> **Bounding Box Convention:** `bbox` is an array of 4 floats: `[x1, y1, x2, y2]` in absolute pixel coordinates corresponding to `frame_size`.

---

## 3. Error Responses

| HTTP Status | Meaning | Typical Cause |
|---|---|---|
| `400 Bad Request` | Could not decode image | Uploaded file is corrupt or not an image. |
| `413 Payload Too Large` | Image exceeds 10 MB limit | Uploaded raw file is larger than 10 MB. |
| `503 Service Unavailable` | Detector not loaded | Model is still initializing during cold startup. |

---

## 4. Tracking Output Contract (`FrameTracks`)

The tracking pipeline (`ai-engine/scripts/track_cameras.py` and downstream streaming modules) extends detection outputs with persistent tracking semantics.

### JSON Schema Structure:
```json
{
  "camera_id": "CAM_001",
  "frame_id": 42,
  "timestamp": "2026-10-05T16:22:30.125Z",
  "frame_size": {
    "width": 1280,
    "height": 720
  },
  "inference_ms": 45.2,
  "objects": [
    {
      "track_id": 14,
      "class": "person",
      "confidence": 0.892,
      "bbox": [412.3, 188.0, 497.9, 402.6],
      "age_s": 3.4
    }
  ]
}
```

### Tracking Fields:
- `track_id` (integer): Persistent object identifier unique within `camera_id`.
- `class` (string): Stable majority-voted class name across the track's lifetime (eliminates single-frame classification flicker).
- `age_s` (float): Track age in seconds since first activation.
- `bbox` (array of 4 floats): `[x1, y1, x2, y2]` clamped pixel coordinates.
- *Note:* `class_id` is intentionally omitted from the tracking contract because `class` reflects the confidence-weighted majority vote, which may supersede individual frame-level class indices.
