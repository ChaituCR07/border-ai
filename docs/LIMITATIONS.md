# Border-AI Platform Technical Limitations & Operational Boundaries

This document provides a transparent, detailed disclosure of the technical constraints, optical boundary conditions, environmental failure modes, and architectural scope boundaries of the Border-AI Video Intelligence Platform (v1.0.0).

---

## 1. Camera Integration & Streaming Boundaries
- **Manual Stream Registration:** IP camera streams must be manually registered with valid RTSP/RTMP URLs (`configs/cameras.json` or via `POST /api/v1/cameras`).
- **No Automated ONVIF Discovery or PTZ Presets:** Automated WS-Discovery of ONVIF cameras and pan-tilt-zoom (PTZ) preset tracking are **not implemented** in v1.0.0. Any ONVIF-conformant camera that exposes standard RTSP video feeds functions reliably.
- **Fixed Static Cameras Required:** The detection and ByteTrack tracking pipelines are calibrated for fixed, stationary pole-mounted CCTV cameras. PTZ cameras during active panning or vehicle-mounted dashboard cameras are out of scope for the benchmarked accuracy numbers.

---

## 2. Computer Vision & Model Performance Boundaries
- **Pretrained Weights:** The default object detector utilizes pretrained YOLOv8s weights without site-specific fine-tuning. Performance on novel industrial machinery or custom border fencing should be validated on-site.
- **Minimum Target Resolution:** Detections require a minimum target height of **32 pixels** for persons and **40 pixels** for vehicles. Small targets at extreme distances (<32 px) experience reduced recall (~42.1%).
- **Occlusion Tracking Drops:** ByteTrack maintains tracks through transient occlusions up to 30 frames. Prolonged occlusion behind physical walls or larger vehicles exceeding 1.0 second may cause a tracker ID switch upon reappearance.

---

## 3. Automated Number Plate Recognition (ANPR) Boundaries
- **Minimum Plate Height:** PaddleOCR PP-OCRv6 requires a minimum license plate crop height of **20 pixels** for reliable recognition. Plates smaller than 20 px or viewed at acute skew angles exceeding $45^\circ$ from the optical axis suffer high character error rates.
- **Plate Geometries:** The pipeline is optimized for single-line and standard high-security registration plates (HSRP). Two-line motorcycle plates, non-standard stylized fonts, or heavily soiled plates may require manual operator review.
- **Environmental Glare:** Direct retro-reflective IR glare from vehicle high-beams or unshielded night illuminators can wash out plate contrast, necessitating polarized lens filters.

---

## 4. Cross-Camera Correlation Boundaries
- **Plate-Dependent Linkage:** Vehicle journey reconstruction relies strictly on license plate recognition. Sightings without a detected license plate cannot be automatically correlated across camera nodes.
- **Clock Synchronization Prerequisite:** Accurate journey sequencing requires all camera nodes and edge recorders to synchronize clocks via Network Time Protocol (NTP). Excessive clock skew (>2.0 seconds) can trigger false impossible-speed anomaly flags.
- **Configured Topology:** The inter-camera adjacency matrix and expected transit times are statically configured (`configs/topology.json`), not automatically learned from traffic density.

---

## 5. Biometric Identity & Re-ID Boundaries
- **Consent-Gated Prototype:** Facial biometric recognition and cross-camera person Re-ID are **prototypes**, disabled by default.
- **Investigative Leads Only:** Facial and appearance matches emit correlation candidate alerts (`REID_MATCH`) intended as investigative leads for human verification, never as definitive autonomous identification.
- **No Search-by-Image:** Free-form image upload search across historical CCTV footage is not implemented.

---

## 6. Environmental Failure Modes (False Positive Triggers)
- **Wet Tarmac Reflections:** Puddle reflections of bright vehicle headlights on wet pavement during heavy rain can create transient bounding box jitter (accounted for by hysteresis debounce).
- **Night IR Insects & Webs:** Spiders spinning webs or insects fluttering within 10 cm of an infrared illuminator cause high-contrast blooms that can trigger motion false alarms without foot-point filtering.
- **Camera Dome Rain Drops:** Unshielded outdoor dome cameras exposed to heavy rain droplets experience localized image distortion, reducing OCR confidence.

---

## 7. Scale & Architecture Boundaries
- **Single-Host Orchestration:** The platform is packaged for single-host Docker Compose deployment. Multi-node distributed clustering (Kubernetes / Helm) is scheduled for post-v1.
- **Single Gateway Process:** The WebSocket gateway maintains sequence counters per process. Horizontal multi-instance load balancing requires the Redis pub/sub global sequence adapter (Future Work).
- **Hardware Capacity ($N^*$):** Sustained throughput SLA (<250ms latency, <1% drops) is benchmarked up to **8 simultaneous RTSP cameras** on the reference Apple Silicon M1 (8 GB) hardware. Scaling to 16+ cameras requires dedicated server-grade GPUs (NVIDIA RTX 3080 / T4).

---

## 8. Security & Identity Boundaries
- **No MFA / SSO:** Authentication supports Argon2id passwords and rotating refresh cookies with least-privilege RBAC. Multi-Factor Authentication (TOTP) and Single Sign-On (OIDC / SAML) are not implemented in v1.0.0.
- **Self-Signed Certificates:** The default quickstart script generates self-signed TLS certificates for `localhost`. Production edge deployments must replace `certs/edge.crt` with an authoritative CA certificate.
- **Deployer Responsibility:** Deploying organizations are solely responsible for physical camera security, network firewalls, data protection compliance (GDPR/DPIA), and statutory retention limits.

---

## 9. Licensing & Commercial Delivery Implications
- **Ultralytics YOLO AGPL-3.0:** The object detection backend incorporates Ultralytics YOLOv8, distributed under the GNU AGPL-3.0. Network-served deployments must provide source code under AGPL-3.0 unless an enterprise commercial license is obtained from Ultralytics, or the detection backend is swapped for an Apache-2.0 alternative (ADR 0054).
