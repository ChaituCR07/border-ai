# Dataset Details and Sources
## AI-Based Intelligent Video Analytics Platform for Border Surveillance

> **Development target:** 3 weeks implementation + 1 week testing/hardening  
> **Purpose:** Personal portfolio, freelancing showcase, and practical AI/video-analytics demonstration.

---

## 1. Dataset Strategy

This project should **not use one dataset for every AI component**. Each module has different data requirements.

| Component | Primary Dataset | Secondary / Custom Dataset | Priority |
|---|---|---|---|
| Object Detection | COCO 2017 | BDD100K | ⭐⭐⭐⭐⭐ |
| Video / Traffic Detection | BDD100K | UA-DETRAC | ⭐⭐⭐⭐⭐ |
| Multi-Object Tracking | MOT17 | BDD100K / UA-DETRAC | ⭐⭐⭐⭐⭐ |
| Vehicle Detection & Tracking | UA-DETRAC | BDD100K | ⭐⭐⭐⭐ |
| ANPR | UFPR-ALPR | CCPD + Custom Indian ANPR | ⭐⭐⭐⭐⭐ |
| ANPR Robustness | CCPD | Custom Indian ANPR | ⭐⭐⭐⭐ |
| Person Re-ID | CUHK03 | Custom multi-camera footage | ⭐⭐⭐ |
| Face Detection | WIDER FACE | Authorized custom footage | ⭐⭐ |
| Drone Extension | VisDrone | — | ⭐ |
| Final End-to-End Testing | **Custom CCTV Dataset** | — | ⭐⭐⭐⭐⭐ |

### Recommended first downloads

For the 4-week project, start with:

1. COCO 2017
2. BDD100K
3. MOT17
4. UFPR-ALPR
5. CCPD
6. Custom Indian ANPR dataset
7. Custom CCTV evaluation dataset

Add CUHK03, WIDER FACE, UA-DETRAC and VisDrone only when the corresponding advanced module is implemented.

---

# 2. COCO 2017

### Official Sources

- Homepage: https://cocodataset.org/
- Detection 2017: https://cocodataset.org/dataset/detection-2017.htm

COCO 2017 provides more than 200,000 images and 80 object categories for detection, with detailed annotations. Useful project classes include `person`, `bicycle`, `car`, `motorcycle`, `bus`, and `truck`.

### Use in this project

```text
COCO
  ↓
Pretrained YOLO
  ↓
Person / Vehicle Detection
```

Use it for:

- Initial model selection
- General object detection
- Baseline testing
- Sanity checks

**Recommendation:** Do not spend the 3-week development window training YOLO from scratch on COCO. Start from an appropriate pretrained detector.

### License note

Verify the current COCO terms before redistribution or commercial use. Do not put the dataset itself into your GitHub repository unless the applicable terms permit redistribution.

---

# 3. BDD100K

### Official Sources

- GitHub: https://github.com/bdd100k/bdd100k
- Homepage: https://bdd-data.berkeley.edu/

BDD100K contains 100,000 driving videos, each around 40 seconds, representing more than 1,000 hours of driving and more than 100 million frames. It supports multiple tasks including object detection and tracking.

### Use in this project

```text
BDD100K
   ↓
YOLO
   ↓
ByteTrack
   ↓
Vehicle / Person Tracking
```

Useful for:

- Video inference
- Traffic scenes
- Person/vehicle detection
- Tracking
- Lighting variation
- Domain validation

### Project timing

**Week 1:** Detection + tracking  
**Week 4:** Robustness/performance testing

### License note

The official repository contains a BSD-3-Clause license for the toolkit/repository. Check the dataset's current terms separately before commercial redistribution.

---

# 4. MOT17

### Official Source

https://motchallenge.net/data/MOT17/

MOT17 is a benchmark for multi-object pedestrian tracking. The official page lists 15,948 training frames and 336,891 annotated pedestrian boxes, with a separate test set.

The complete MOT17 download is currently listed as approximately 5.5 GB; the annotations/detection-only package is much smaller.

### Use in this project

```text
MOT17
   ↓
Detector outputs
   ↓
ByteTrack
   ↓
Track IDs / Trajectories
```

Evaluate:

- Track continuity
- ID switches
- Detection-to-track association
- Trajectory consistency

### Project timing

**Week 1:** Tracking development  
**Week 4:** Tracking evaluation

---

# 5. UA-DETRAC

### Official Sources

- Project: https://sites.google.com/view/daweidu/projects/ua-detrac
- Research paper: https://doi.org/10.1016/j.cviu.2020.102907

UA-DETRAC is focused on vehicle detection and multi-object tracking in traffic surveillance. It contains 100 challenging videos, more than 140,000 frames and about 1.21 million vehicle bounding boxes, with annotations such as vehicle type, illumination, occlusion and truncation.

### Vehicle classes

```text
Car
Bus
Van
Other
```

### Use in this project

```text
UA-DETRAC
     ↓
Vehicle Detector
     ↓
Vehicle Tracker
     ↓
Trajectory Evaluation
```

### Priority

Optional for the 4-week MVP. Use it when you want stronger vehicle-specific evaluation.

---

# 6. UFPR-ALPR

## Most relevant research dataset for ANPR

### Official Sources

- Dataset: https://web.inf.ufpr.br/vri/databases/ufpr-alpr/
- License: https://web.inf.ufpr.br/vri/databases/ufpr-alpr/license-agreement/

UFPR-ALPR contains 4,500 fully annotated 1,920 × 1,080 images from 150 vehicles and more than 30,000 license-plate characters. The data was captured with three cameras and includes cars and motorcycles.

### Split

```text
Training:   40%
Testing:    40%
Validation: 20%
```

### Annotations

- Camera information
- Vehicle position
- Vehicle type
- Manufacturer/model/year
- License plate identity
- License plate position
- Character positions

### Project pipeline

```text
Vehicle
   ↓
Plate Detection
   ↓
Plate Crop
   ↓
Preprocessing
   ↓
PaddleOCR
   ↓
Plate Number
```

### Critical licensing restriction

UFPR-ALPR is released for academic research/non-commercial purposes. The official license states that redistribution, modification and commercial usage require expressed permission. Use it for research/benchmarking according to its terms; do not package or redistribute it as part of a commercial client product.

### Access

The official license page requires an institutional/university request and agreement to its terms.

---

# 7. CCPD

## Chinese City Parking Dataset

### Official Source

https://github.com/detectRecog/CCPD

The updated CCPD release contains more than 300,000 images and multiple challenging subsets.

### Useful subsets

```text
CCPD-Base
CCPD-DB
CCPD-Blur
CCPD-FN
CCPD-Rotate
CCPD-Tilt
CCPD-Challenge
CCPD-Green
```

### Use for

- Plate localization
- OCR robustness
- Blur
- Rotation
- Tilt
- Perspective
- Challenging plates

### Important limitation

CCPD primarily represents Chinese license plates. It should therefore **not be the only ANPR dataset for an India-focused system**.

Use it for general plate-detection/OCR robustness and supplement it with Indian data.

### License

The official repository describes the dataset as open-source under MIT and asks users to cite the ECCV 2018 paper. Always check the current repository terms before commercial redistribution.

---

# 8. Custom Indian ANPR Dataset

## Recommended project dataset

This should become the most important dataset for the India-focused ANPR component.

### Suggested name

```text
BorderVision-India-ANPR
```

### Target size

```text
500–2,000 images
```

A small, carefully annotated dataset is sufficient for an MVP/fine-tuning experiment.

### Annotation structure

```json
{
  "image": "IMG_0001.jpg",
  "vehicle_bbox": [120, 180, 820, 640],
  "plate_bbox": [420, 500, 590, 550],
  "plate_text": "KA01AB1234"
}
```

### Data diversity

Include:

- Day
- Night
- Rain
- Blur
- Low light
- Different angles
- Different distances
- Cars
- Motorcycles
- Buses
- Trucks
- Multiple Indian registration regions

Example prefixes:

```text
KA
TN
AP
TS
KL
MH
DL
GJ
RJ
UP
```

### Data collection rule

Only use footage/images that you own, have permission to use, or are explicitly licensed for your intended use. For the portfolio, controlled/authorized footage is preferable.

---

# 9. Custom CCTV Evaluation Dataset

## Most important dataset for the final demo

### Suggested name

```text
BorderVision-CCTV-MVP
```

### Target

```text
10–20 short videos
30–120 seconds each
3–5 simulated cameras
```

### Folder structure

```text
BorderVision-CCTV-MVP/
│
├── camera_01/
│   ├── normal/
│   ├── restricted_zone/
│   ├── line_crossing/
│   └── night/
│
├── camera_02/
│   ├── normal/
│   ├── vehicles/
│   ├── watchlist/
│   └── night/
│
├── camera_03/
│   ├── normal/
│   ├── loitering/
│   └── vehicle_tracking/
│
└── annotations/
```

### Controlled scenarios

1. Person enters restricted zone
2. Person loiters for more than 60 seconds
3. Vehicle crosses virtual line
4. Vehicle travels in wrong direction
5. Watchlist vehicle enters restricted zone
6. Same vehicle appears on multiple cameras
7. Night-time vehicle movement
8. Multiple vehicles simultaneously

This dataset is more useful for the final product demonstration than random CCTV footage because every alert can be deliberately reproduced.

---

# 10. CUHK03

## Purpose: Person Re-Identification

### Official Source

https://www.ee.cuhk.edu.hk/~xgwang/CUHK_identification.html

CUHK03 contains 1,360 identities and 13,164 images, including manually cropped and automatically detected person images.

### Pipeline

```text
Camera 1
    ↓
Person Crop
    ↓
Re-ID Embedding
    ↓
Camera 2
    ↓
Person Crop
    ↓
Re-ID Embedding
    ↓
Similarity
    ↓
Potential Same Identity
```

### Use

Primarily for Re-ID research/validation. For the final portfolio demo, use authorized multi-camera footage.

---

# 11. WIDER FACE

## Purpose: Face Detection

### Official Source

https://mmlab.ie.cuhk.edu.hk/projects/WIDERFace/

WIDER FACE contains 32,203 images and 393,703 labeled faces, with large variation in scale, pose and occlusion.

### Split

```text
Training:   40%
Validation: 10%
Testing:    50%
```

### Pipeline

```text
CCTV
 ↓
Person Detection
 ↓
Face Detection
 ↓
Face Crop
 ↓
Face Embedding
```

### Priority

Optional. The main MVP should work without facial recognition.

---

# 12. VisDrone

## Purpose: Drone / Aerial Extension

### Official Source

https://github.com/VisDrone/VisDrone-Dataset

VisDrone provides annotated image/video data for object detection, single-object tracking, multi-object tracking and crowd counting.

### Potential future architecture

```text
CCTV + Drone Camera
        ↓
Unified AI Inference
        ↓
Event Engine
        ↓
Command Dashboard
```

### Priority

Low for the current 4-week project. Keep it as a future extension.

---

# 13. AOLP

## Application-Oriented License Plate Recognition

### Official Source

https://github.com/AvLab-CV/AOLP

AOLP contains 2,049 images covering access control, traffic law enforcement and road patrol scenarios.

### Restrictions

The official repository states that:

- Redistribution is not permitted.
- Sharing requires permission.
- The database cannot be posted outside the authorized research group.
- No economic profit may be made from the database.
- Publications using it must cite the paper.

### Recommendation

Use AOLP only as an additional research benchmark if necessary. **Do not use it as a commercial/client dataset.**

---

# 14. Dataset-to-Model Mapping

| Dataset | Component | Model / Method | Main Usage |
|---|---|---|---|
| COCO | Object Detection | YOLO | Baseline |
| BDD100K | Video Detection | YOLO | Domain validation |
| MOT17 | Tracking | ByteTrack | Tracking evaluation |
| UA-DETRAC | Vehicle Tracking | YOLO + ByteTrack | Vehicle evaluation |
| UFPR-ALPR | ANPR | Plate detector + OCR | Research benchmark |
| CCPD | ANPR | Detector + OCR | Robustness |
| Custom Indian ANPR | ANPR | Detector + OCR | **Main India-specific dataset** |
| CUHK03 | Re-ID | Re-ID model | Cross-camera research |
| WIDER FACE | Face Detection | Face detector | Optional |
| VisDrone | Aerial Detection/Tracking | YOLO + tracker | Optional |
| Custom CCTV | Full System | Complete pipeline | **Final demo** |

---

# 15. Dataset Usage by Week

## Week 1 — Detection and Tracking

```text
COCO
BDD100K
MOT17
```

```text
BDD100K / MOT17
       ↓
YOLO
       ↓
ByteTrack
       ↓
Zones
       ↓
Line Crossing
```

## Week 2 — ANPR and Intelligence

```text
UFPR-ALPR
CCPD
Custom Indian ANPR
```

```text
Vehicle
   ↓
Plate Detection
   ↓
PaddleOCR
   ↓
Plate Number
   ↓
Watchlist
```

## Week 3 — Product Integration

Use primarily the custom CCTV footage:

```text
Camera 1
Camera 2
Camera 3
     ↓
AI Engine
     ↓
Redis Streams
     ↓
PostgreSQL
     ↓
Dashboard
```

## Week 4 — Evaluation

```text
MOT17
    → Tracking evaluation

UFPR-ALPR / CCPD
    → ANPR evaluation

BDD100K
    → Video robustness

Custom CCTV
    → End-to-end evaluation
```

---

# 16. Recommended Dataset Folder Structure

```text
datasets/
│
├── detection/
│   ├── coco/
│   ├── bdd100k/
│   └── ua-detrac/
│
├── tracking/
│   ├── mot17/
│   └── bdd100k/
│
├── anpr/
│   ├── ufpr-alpr/
│   ├── ccpd/
│   └── india-custom/
│
├── reid/
│   └── cuhk03/
│
├── face/
│   └── wider-face/
│
├── aerial/
│   └── visdrone/
│
└── validation/
    └── bordervision-cctv/
```

---

# 17. Do Not Put the Actual Datasets in GitHub

The repository should contain:

```text
datasets/
└── README.md
```

rather than the complete datasets.

`datasets/README.md` should document:

- Official dataset URL
- Download procedure
- Dataset version
- License/terms
- Expected folder structure
- Preprocessing
- Train/validation/test split
- Citation

This avoids unnecessary redistribution of third-party datasets.

---

# 18. Dataset License Checklist

Create a separate file:

```text
DATASET_LICENSES.md
```

Recommended tracking table:

| Dataset | Purpose | Redistribution | Commercial Use | Action |
|---|---|---|---|---|
| COCO | Detection | Check current terms | Check current terms | Verify |
| BDD100K | Video/detection | Check dataset terms | Verify | Verify |
| MOT17 | Tracking | Check dataset terms | Verify | Verify |
| UA-DETRAC | Vehicle tracking | Check dataset terms | Verify | Verify |
| UFPR-ALPR | ANPR research | Restricted | No without permission | Research only |
| CCPD | ANPR | Review current repository terms | Verify | Research/benchmark |
| CUHK03 | Re-ID | Check dataset terms | Verify | Research |
| WIDER FACE | Face detection | Check dataset terms | Verify | Research |
| AOLP | ANPR | No | No economic profit | Do not use commercially |
| Custom CCTV | Final testing | Depends on ownership | Depends on rights | Authorized footage |
| Custom Indian ANPR | ANPR | Depends on source data | Depends on source rights | Preferred |

**Important:** Dataset licensing and model licensing are separate. Maintain a second `MODEL_LICENSES.md` for YOLO, OCR, Re-ID and face models.

---

# 19. Final Recommended Dataset Set

## MUST HAVE

### COCO 2017
General object detection.

### BDD100K
Video and traffic detection/tracking.

### MOT17
Multi-object tracking evaluation.

### UFPR-ALPR
ANPR research benchmark.

### CCPD
ANPR robustness.

### Custom Indian ANPR
India-specific plate adaptation.

### Custom CCTV Evaluation Dataset
Final end-to-end demonstration.

## OPTIONAL

- CUHK03 → Person Re-ID
- UA-DETRAC → Vehicle-specific tracking
- WIDER FACE → Face detection
- VisDrone → Drone integration
- AOLP → Additional ANPR research benchmark

---

# 20. Dataset Download Checklist

```text
[ ] COCO / pretrained model environment
[ ] BDD100K
[ ] MOT17
[ ] UFPR-ALPR access requested
[ ] CCPD
[ ] Custom Indian ANPR dataset plan
[ ] Custom CCTV videos
[ ] Dataset license documentation
[ ] Dataset preprocessing scripts
[ ] Train/validation/test split definitions
[ ] Dataset versions recorded
```

---

# 21. Final Dataset Architecture

```text
              PUBLIC DATASETS
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
     COCO        BDD100K       MOT17
       │            │            │
       └────────────┼────────────┘
                    ▼
              BASE AI MODELS
                    │
                    ▼
             DOMAIN DATASETS
                    │
             ┌──────┴──────┐
             ▼             ▼
          UFPR-ALPR       CCPD
             │             │
             └──────┬──────┘
                    ▼
             INDIA CUSTOM ANPR
                    │
                    ▼
             YOUR AI PIPELINE
                    │
                    ▼
          CUSTOM CCTV DATASET
                    │
                    ▼
             FINAL PRODUCT
```

The strongest portfolio story is therefore:

> **Pretrained AI → Benchmark datasets → Domain-specific data → Custom Indian data → Real-time product.**

---

# 22. Primary Sources

1. COCO: https://cocodataset.org/
2. COCO 2017 Detection: https://cocodataset.org/dataset/detection-2017.htm
3. BDD100K: https://github.com/bdd100k/bdd100k
4. BDD100K Homepage: https://bdd-data.berkeley.edu/
5. MOT17: https://motchallenge.net/data/MOT17/
6. UA-DETRAC: https://sites.google.com/view/daweidu/projects/ua-detrac
7. UFPR-ALPR: https://web.inf.ufpr.br/vri/databases/ufpr-alpr/
8. UFPR-ALPR License: https://web.inf.ufpr.br/vri/databases/ufpr-alpr/license-agreement/
9. CCPD: https://github.com/detectRecog/CCPD
10. CUHK03: https://www.ee.cuhk.edu.hk/~xgwang/CUHK_identification.html
11. WIDER FACE: https://mmlab.ie.cuhk.edu.hk/projects/WIDERFace/
12. VisDrone: https://github.com/VisDrone/VisDrone-Dataset
13. AOLP: https://github.com/AvLab-CV/AOLP

---

# 23. Final Recommendation

For this 4-week project, do **not** train a separate model on every dataset.

Use:

```text
COCO
  ↓
General Detection

BDD100K
  ↓
Video / Traffic Validation

MOT17
  ↓
Tracking Validation

UFPR-ALPR + CCPD
  ↓
ANPR Research / Robustness

Custom Indian ANPR
  ↓
India-specific Adaptation

Custom CCTV
  ↓
Final End-to-End Product Testing
```

This creates a clear technical progression:

```text
General Computer Vision
        ↓
Domain Validation
        ↓
ANPR
        ↓
Tracking
        ↓
Custom Indian Data
        ↓
Real-Time Event Intelligence
        ↓
Multi-Camera Correlation
        ↓
Production-Style Dashboard
```
