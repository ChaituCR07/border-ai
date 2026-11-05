# Model Card: BorderVision Surveillance Object Detector

## 1. Model Details
- **Model Name:** BorderVision Surveillance Object Detector
- **Architecture:** YOLOv8 (nano / small / medium variants)
- **Primary Task:** Multi-class object detection (person, car, truck, bus, motorcycle)
- **Version:** v1.0.0
- **Release Date:** 2026-11-04
- **Licence:** AGPL-3.0 (Ultralytics) / Commercial dual-license options
- **Citations:** Jocher et al. (2023), *Ultralytics YOLOv8*; Lin et al. (2014), *Microsoft COCO: Common Objects in Context*

## 2. Intended Use & Out-of-Scope Use
- **Intended Use:**
  - Automated visual cueing for checkpoint perimeter monitoring.
  - Border zone intrusion detection and vehicle flow counting.
  - Providing region proposals to downstream tracking and ANPR modules.
  - Decision support tool for human border security operators.
- **Out-of-Scope Use:**
  - Autonomous lethal force triggering or autonomous weapon targeting.
  - Individual identity profiling or biometric classification.
  - Standalone punitive ticketing without human officer verification.

## 3. Factors & Environmental Conditions
- **Supported Camera Geometries:** Pole-mounted, static overhead CCTV ($3.0\,\text{m} - 6.5\,\text{m}$ mounting height), depression angle $15^\circ - 35^\circ$.
- **Illumination:** Optimal in daylight ($\ge 200\,\text{lux}$); functional in night scenes with active infrared (IR) illumination or fixed perimeter sodium-vapor lighting.
- **Weather Degradation:** Performance degrades under torrential monsoon rain, heavy ground fog, and lens water spotting.

## 4. Benchmark Metrics & Operating Points
- **Primary Operating Point (Surveillance Balanced, Conf $\ge 0.35$, NMS IoU $0.45$):**
  - **mAP@0.5:** $78.4\%$ $[75.2\%, 81.3\%]$ ($n=1,240$ images, `coco-surveillance-val`, run `run-20261104-det-eval-01`, 2026-11-04).
  - **mAP@0.5:0.95:** $54.2\%$ $[51.0\%, 57.1\%]$ ($n=1,240$ images, run `run-20261104-det-eval-01`).
  - **Person Recall@0.5:** $86.1\%$ $[83.4\%, 88.5\%]$.
  - **Vehicle Recall@0.5:** $91.8\%$ $[89.6\%, 93.7\%]$.
- **Inference Latency:**
  - Jetson Orin Nano (TensorRT FP16, $640\times 640$): $14.2\,\text{ms}$ / frame ($70.4\,\text{FPS}$).
  - CPU Fallback (Intel Core i7-1185G7, ONNX Runtime): $48.5\,\text{ms}$ / frame.

## 5. Evaluation Data
- **COCO Surveillance Subset (`coco-surveillance-val`):** 1,240 images filtered for person and ground vehicle classes.
- **BorderVision Perimeter Field Test:** 320 high-definition frames captured at designated perimeter test zones.
- **Class Mapping Policy:** ADR 0036 standardizes vehicle subtypes into the unified security ontology.

## 6. Ethical Considerations & Privacy Risks
- **Surveillance Proportionality:** Bounding boxes are generated solely within designated border perimeter and access-control coordinates.
- **Privacy Filtering:** Bounding boxes and confidence values are transmitted; raw imagery is processed on edge hardware and discarded unless flagged for security review.

## 7. Operational Recommendations
- Ensure minimum object size in frame $\ge 32\times 32\,\text{pixels}$ for reliable recall.
- Clean optical camera domes every 30 days in dusty checkpoint environments.
