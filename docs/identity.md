# Face Watchlist & Cross-Camera Re-ID Guide

Day 10 introduces the identity processing subsystem, providing facial watchlist correlation and cross-camera person re-identification.

---

## 1. Pipeline Overview

```text
Person Track (YOLOv8 + ByteTrack)
       │
       ▼
Upper-Body / Person Crop (copied before rendering)
       │
       ├─────────────────────────────────┬─────────────────────────────────┐
       ▼                                                                   ▼
[Face Path]                                                        [Re-ID Path]
Face Detection (YuNet / SCRFD)                                     Appearance Embedding (ColorLayout / ONNX)
       │                                                                   │
Quality Gate (Score >= 0.8, Size >= 40px, Yaw <= 0.5, Sharpness)  Add to Track Aggregator
       │                                                                   │
Face Embedding (SFace 128-d / ArcFace 512-d)                       Enough Samples (>= 3)?
       │                                                                   │
Track Aggregator & Consistency Check (>= 0.75)                     Search Recent Cross-Camera Gallery
       │                                                                   │
Search FaceGallery (Cosine Similarity)                             Top Candidate >= 0.90?
       │                                                                   │
Best Match Margin Check (>= 0.05)                                  Emit REID_MATCH (status: candidate)
       │                                                           Label: "= CAM_001 #12?"
Emit WATCHLIST_MATCH (status: review)
Store Hit (match_basis: face)
Flag Track: "HIGH REVIEW FACE"
```

---

## 2. Tools & Scripts

### Face Smoke Test
Verify detector and recognizer functionality on local images:
```bash
python ai-engine/scripts/face_smoke_test.py --image path/to/photo1.jpg --image2 path/to/photo2.jpg
```

### Consent-Gated Enrollment
Enrol a consenting individual from several reference photos:
```bash
python ai-engine/scripts/face_enroll.py \
    --folder path/to/subject_photos/ \
    --identifier subject-001 \
    --name "Consenting Volunteer" \
    --risk LOW \
    --consent-confirmed
```

### Face Recognition Evaluation
Evaluate genuine vs. impostor similarity distributions across multi-person datasets:
```bash
python ai-engine/scripts/face_eval.py --folder datasets/faces/
```

### Person Re-ID Evaluation
Evaluate cross-camera rank-k retrieval on multi-camera person crops:
```bash
python ai-engine/scripts/reid_eval.py --folder datasets/reid/ --embedder color_layout
```

---

## 3. Known Limitations & Failure Modes

1. **Low Resolution & Extreme Angles:** CCTV mounted high above subjects produces steep pitch angles and small face crops (< 40 px), which are safely skipped by the quality gate.
2. **Tracker ID Switches:** If ByteTrack momentarily swaps IDs between crossing pedestrians, the multi-frame consistency check detects embedding divergence and cancels matching.
3. **Clothing-Based Re-ID:** The `ColorLayoutEmbedder` relies on color distribution; subjects wearing similar uniforms or dark outerwear may match each other. Every Re-ID event is classified as `candidate` requiring operator confirmation.
