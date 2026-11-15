# ADR 0054: Open-Source Licensing, Third-Party Notices, and Responsible Use Policy

## Status
Accepted

## Context
The Border-AI platform integrates state-of-the-art open-source dependencies across machine learning (Ultralytics YOLO, PaddleOCR, OpenCV), backend services (Node.js, Fastify, Prisma, PostgreSQL, Redis), frontend libraries (React, Vite, TailwindCSS), and evaluation datasets (COCO, BDD100K, MOT17).

Critically:
- Ultralytics YOLOv8 is distributed under the GNU Affero General Public License v3.0 (AGPL-3.0), which enforces copyleft provisions on networked derivative works unless a commercial enterprise license is acquired.
- PaddleOCR is distributed under Apache 2.0.
- Computer vision datasets (COCO, BDD100K, MOT17) are licensed strictly for non-commercial academic and research evaluation.
- Surveillance and video intelligence technologies present ethical and privacy implications that require explicit deployment guidelines, consent gates, and data protection boundaries.

## Decision

1. **Platform Repository License:**
   - The Border-AI project code is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)** to maintain full legal compliance with upstream Ultralytics YOLOv8 dependencies.
   - For commercial client delivery, the documentation clearly states that clients must either:
     a) Purchase an Ultralytics enterprise commercial license, or
     b) Swap the detection backend for a permissively licensed alternative (e.g., ONNX/TensorRT-converted models or Apache-2.0 detectors).

2. **Third-Party Notices & Attribution:**
   - Maintain `NOTICE` and `THIRD_PARTY_LICENSES.md` documenting direct dependencies and their licenses.
   - Maintain explicit `MODEL_LICENSES.md` and `DATASET_LICENSES.md` files confirming that zero raw proprietary evaluation dataset images or video labels are committed to git.

3. **Responsible Use Framework (`docs/RESPONSIBLE_USE.md`):**
   - **Intended Use:** Operational decision support for authorized security operators on controlled perimeter, gate, and critical infrastructure installations.
   - **Prohibited Use:** Autonomous enforcement or weapon systems, warrantless public mass surveillance, covert person tracking, discrimination or profiling of protected classes.
   - **Privacy-by-Design Defaults:** Biometric facial recognition and Re-ID are disabled by default and require explicit consent-referenced enrollment; raw biometric embeddings are excluded from API payloads; forensic data retention is automatically enforced.
   - **Legal Disclaimer:** Deploying organizations bear full legal responsibility for compliance with regional surveillance laws (GDPR, CCPA, local data privacy regulations).

## Consequences

- Legal risk is transparently addressed and mitigated for open-source users and prospective freelance clients.
- The project demonstrates enterprise-level compliance maturity and ethical responsibility.
