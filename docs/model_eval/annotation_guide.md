# Ground-Truth Annotation Guidelines for Border CCTV Surveillance

## 1. Objective
This document defines annotation standards for curating custom evaluation datasets on border CCTV feeds. High-quality ground truth ensures that detection and tracking benchmarks accurately reflect physical security requirements.

---

## 2. Bounding Box Annotation Standards

### 2.1 Bounding Box Tightness
- Bounding boxes must enclose all visible pixels belonging to the target object.
- **Do not include cast shadows** on the ground or walls within the bounding box.
- For pedestrians carrying backpacks or handheld items (e.g. tools, bags), include the carried items if physically affixed to the body.

### 2.2 Foot-Point Ground Plane Alignment
- Because perimeter line crossing and exclusion zones rely on foot-point coordinates `(x + w/2, y + h)`, the bottom edge of the box **must align precisely with the contact plane** where feet touch the ground.
- If feet are occluded by grass or low berms, estimate ground plane contact based on visible anatomy.

### 2.3 Partial Occlusion & Truncation
- **Occluded Targets:** If an object is partially behind a fence or pole, draw the bounding box across the entire extent of the subject. Mark attribute `"occluded": true`.
- **Heavy Occlusion (> 80%):** Objects occluded by more than 80% should be marked `"ignore": true`.
- **Frame Boundary Truncation:** If a subject is partially outside the field of view, mark `"truncated": true`.

---

## 3. Multi-Camera Tracking Annotation Rules

### 3.1 Consistent Track Identity
- A subject entering the field of view is assigned a unique positive integer `track_id`.
- The `track_id` **must persist across brief occlusions** (such as walking behind a security booth or light pole).
- If a subject exits the camera view and re-enters more than 10 seconds later, assign a new `track_id` unless multi-camera re-identification ground truth is explicitly being annotated.

### 3.2 Crowd & Distractor Regions
- Densely packed groups where individual boundaries cannot be distinguished must be annotated with a single encompassing box marked `"ignore": true` and `"category": "crowd"`.
- Static mannequins, human silhouettes on signs, or billboard graphics must be marked `"ignore": true`.

---

## 4. Format & Schema
Custom CCTV annotations must be formatted according to `evaluation/datasets/cctv_custom.py`:
```json
{
  "images": [
    {
      "id": "cctv_cam01_00123",
      "file_name": "cam01_00123.jpg",
      "camera_id": "cctv_north_gate",
      "width": 1920,
      "height": 1080,
      "environment": {
        "time_of_day": "night",
        "weather": "rain",
        "infrared": true
      },
      "annotations": [
        {
          "category": "person",
          "bbox": [240.0, 480.0, 50.0, 120.0],
          "track_id": 42,
          "ignore": false,
          "attributes": {
            "occluded": false,
            "truncated": false
          }
        }
      ]
    }
  ]
}
```
