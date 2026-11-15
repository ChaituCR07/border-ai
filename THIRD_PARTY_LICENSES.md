# Border-AI Third-Party Software & Model Licenses Audit

This document catalogs third-party dependencies, machine learning models, and evaluation datasets incorporated into or referenced by the Border-AI Video Intelligence Platform.

---

## 1. Machine Learning Models & Weights

| Model Artifact | Origin / Author | Architecture / Version | Upstream License | Intended Use / Distribution Note |
|---|---|---|---|---|
| **YOLOv8s Detector** | Ultralytics Inc. | YOLOv8 Small (`yolov8s.pt`) | **AGPL-3.0** | Real-time object detection (`person`, `car`, `truck`, `bus`, `motorcycle`). Model weights fetched via SHA-256 lockfile (`configs/models.lock.json`). Commercial delivery requires an Ultralytics commercial license or switching to an Apache-2.0 detector. |
| **PaddleOCR PP-OCRv6** | PaddlePaddle Authors | PP-OCRv6 Text Detection & Recognition | **Apache-2.0** | License plate character OCR and multi-frame consensus. |
| **YuNet Face Detector** | Shiqi Yu et al. / OpenCV | YuNet Lightweight Face Detector | **Apache-2.0** | Consent-gated face detection prototype. |
| **SFace Feature Extractor** | Zhong et al. / OpenCV | SFace SphereFace 128-d Embedding | **Apache-2.0** | Consent-gated facial feature representation. |

---

## 2. Evaluation Datasets (Research & Offline Benchmark Only)

**Zero raw proprietary dataset media, frames, or bounding box annotations are committed to this Git repository.** All benchmark datasets are downloaded offline into local cache directories (`datasets/`) during evaluation runs:

| Dataset | Custodian / Citation | License / Terms | Scope in Border-AI |
|---|---|---|---|
| **COCO (Common Objects in Context)** | Microsoft / COCO Consortium | Creative Commons Attribution 4.0 (CC-BY 4.0) | COCO-1000 deterministic benchmark evaluation split for object detection baseline. |
| **BDD100K** | UC Berkeley / Fisher et al. | BSD 3-Clause / Academic Research License | BDD100K-500 dev and test splits for road scene evaluation. |
| **MOT17** | Milan et al. / MOT Challenge | Non-commercial Academic Research Use | MOT17 static CCTV camera splits (`MOT17-02`, `MOT17-04`, `MOT17-09`) for ByteTrack tracking evaluation. |

---

## 3. Core Runtime Dependencies

### Python Ecosystem (AI Engine & Video Ingestion)
- **`torch` / `torchvision`:** BSD-3-Clause (PyTorch Foundation)
- **`ultralytics`:** GNU AGPL-3.0 (Ultralytics Inc.)
- **`opencv-python-headless`:** Apache-2.0 (OpenCV Foundation)
- **`paddleocr` / `paddlepaddle`:** Apache-2.0 (PaddlePaddle Authors)
- **`psycopg[binary,pool]`:** GNU LGPL-3.0 with runtime exception
- **`redis`:** MIT License (Redis Ltd.)
- **`numpy`:** BSD-3-Clause
- **`pydantic`:** MIT License

### Node.js & TypeScript Ecosystem (Backend API & WebSocket Gateway)
- **`fastify`:** MIT License
- **`@fastify/cors`, `@fastify/rate-limit`, `@fastify/helmet`:** MIT License
- **`zod` / `fastify-type-provider-zod`:** MIT License
- **`@prisma/client` / `prisma`:** Apache-2.0
- **`ioredis`:** MIT License
- **`argon2`:** MIT License
- **`nodemailer`:** MIT License

### Frontend Web Ecosystem (Operator Command Center)
- **`react` / `react-dom`:** MIT License (Meta Platforms, Inc.)
- **`vite`:** MIT License (Evan You & Vite Contributors)
- **`tailwindcss`:** MIT License
- **`lucide-react`:** ISC License
- **`@tanstack/react-query`:** MIT License

### Edge & Infrastructure Services
- **`nginx`:** 2-Clause BSD License
- **`postgresql`:** PostgreSQL Open Source License
- **`redis`:** 3-Clause BSD License
- **`mediamtx`:** MIT License (bluenviron)

---

## 4. Commercial Client Delivery & Dual-Licensing Guidance

For software consultants, integrators, and clients seeking to deliver Border-AI commercially:
1. **Ultralytics AGPL-3.0 Considerations:** Because Ultralytics YOLO is governed by AGPL-3.0, any networked service using YOLOv8 must offer corresponding source code to network users under AGPL-3.0.
2. **Commercial Deployment Pathways:**
   - **Pathway A (Commercial YOLO License):** Purchase an enterprise license directly from Ultralytics to eliminate copyleft obligations.
   - **Pathway B (Permissive Detector Swap):** The Border-AI detection interface (`engine/detector/base.py`) is modular. Deployers can substitute YOLOv8 with Apache-2.0 or MIT-licensed detectors (e.g., RT-DETR, MobileNet-SSD, or TensorRT-optimized open-source weights) without modifying the downstream ByteTrack, ANPR, rule engine, or dashboard tiers.
