# Detection Notes & Threshold Experiments (Day 3)

## 1. Parameter Sensitivity & Trade-offs

| Parameter | Flag | Description | Low Setting Trade-off | High Setting Trade-off |
|---|---|---|---|---|
| **Confidence Threshold** | `--conf` | Minimum score required to report a bounding box | Excessive false positives, flickering detections on background clutter | Missed real objects (especially distant or partially occluded subjects) |
| **NMS IoU Threshold** | `--iou` | Overlap threshold above which lower-confidence duplicate boxes are suppressed | Tightly packed real objects (e.g. crowds or traffic) are mistakenly suppressed | Duplicate or split boxes on single large objects |
| **Image Size** | `--imgsz` | Square resolution fed to YOLO backbone (e.g., 640, 960) | Small objects lose pixel resolution and are missed, but inference is 2x faster | Distant objects detected accurately, but latency doubles |

---

## 2. Threshold Experiments Observation Log

| Frame / Clip | Setting Tested | Latency (ms) | Observed Behavior & Notes |
|---|---|---|---|
| `person_frame.jpg` | `conf=0.25, iou=0.5, imgsz=640` | ~47 ms | Captures faint candidate proposals; higher risk of noise in complex backgrounds. |
| `person_frame.jpg` | `conf=0.40, iou=0.5, imgsz=640` | ~50 ms | **Optimal default:** clean background suppression with solid candidate retention. |
| `person_frame.jpg` | `conf=0.60, iou=0.5, imgsz=640` | ~50 ms | Overly conservative; distant or low-contrast targets are dropped. |
| `crowded_frame.jpg` | `conf=0.40, iou=0.45, imgsz=640` | ~53 ms | Aggressive NMS deduplication; risks merging adjacent overlapping targets. |
| `crowded_frame.jpg` | `conf=0.40, iou=0.70, imgsz=640` | ~45 ms | Relaxed NMS; preserves close pedestrians but permits occasional duplicate boxes. |
| `crowded_frame.jpg` | `conf=0.40, iou=0.50, imgsz=960` | ~110 ms | High-resolution inference; sharp details but latency doubles (~9 FPS throughput). |

---

## 3. Justification of Selected Working Defaults (`configs/app.yaml`)

- `confidence: 0.4`: Prevents false security alarms from atmospheric shadow/vegetation noise while retaining genuine person/vehicle encounters.
- `iou: 0.5`: Standard balance between separating individual subjects in groups and eliminating duplicate boxes.
- `image_size: 640`: Standard YOLO resolution providing real-time inference (~20 FPS) without excessive GPU/CPU thermal throttling.
- `max_det: 300`: Safeguards memory buffers against pathological scenes with hundreds of candidate proposals.

---

## 4. Multi-Camera Capacity Arithmetic

- **Target Workload:** 3 cameras running at 15 FPS = **45 frames/second** total throughput required.
- **Sequential Compute Capacity:** Single-thread inference averages ~50 ms per frame = **20 inferences/second** maximum throughput.
- **Consequence:** Under sequential host execution, `CameraManager` drops frames by design (~55% drop rate across 3 streams) to ensure zero buffer delay and real-time responsiveness.
- **Optimization Roadmap (Day 4):** FP16 half-precision and batched multi-camera inference will be introduced to saturate the required 45 FPS budget.
