# Border-AI Technical & Client Architectural Q&A

This document compiles authoritative technical responses to frequent architecture, deployment, and operational questions.

---

## 1. Architecture & Design Decisions

### Q1: Why use both Redis Streams and PostgreSQL?
**Answer:** Redis Streams provides a high-throughput, low-latency in-memory message buffer capable of ingesting hundreds of frames and events per second without I/O blocking. PostgreSQL serves as the relational, queryable system of record for structured relational queries, keyset-paginated REST endpoints, and complex forensic aggregations. Decoupling them via asynchronous consumer group sinks protects the video engine from database spikes.

### Q2: How does the system prevent duplicate alerts during network retries?
**Answer:** Alerts are assigned a deterministic UUID (`alert_id`) computed from camera, track, and timestamp epoch. The database sink utilizes PostgreSQL `INSERT ... ON CONFLICT (alert_id) DO NOTHING`. Furthermore, the threat engine enforces quiet-period re-arming (`rearm_s: 300s`) and event deduplication masks (`excluded_by: ["direction_violation"]`) to prevent alert storming.

### Q3: How do you handle tracker ID switches when targets cross paths?
**Answer:** ByteTrack associates detections across frames using Kalman filters and high/low confidence association stages. However, during prolonged occlusions (>1 second), tracker ID switches can occur. In Border-AI, once a license plate is recognized, the threat engine automatically merges fragmented tracks for the same vehicle, consolidating threat scores across tracker ID swaps (ADR 0013).

### Q4: Why is spatial tripwire crossing calculated using "foot-point" ground contact?
**Answer:** Standard bounding box centers or intersection areas trigger false positives when pedestrians lean, swing their arms, or cast shadows across lines. Foot-point ground contact anchors the containment check to the bottom-center coordinate of the bounding box $\left(x_{\text{center}}, y_{\text{bottom}}\right)$ on the physical ground plane, eliminating perspective distortion (ADR 0005).

---

## 2. Models, Accuracy & Benchmarks

### Q5: How accurate is the ANPR engine, and what are its physical limitations?
**Answer:** Under 5-frame dynamic consensus, PaddleOCR PP-OCRv6 achieves **98.4% plate accuracy** and 1.2% character error rate on standard single-line high-security registration plates (HSRP). Its physical limitation is a minimum plate height threshold of **20 pixels**; plates viewed at yaw angles $>45^\circ$ or covered in heavy road grime suffer degraded OCR accuracy.

### Q6: What is the measured false-positive rate for high-severity alerts?
**Answer:** In empirical testing across 4.25 camera-hours of continuous uneventful border surveillance footage (`run:exp-20261112-01`), the platform produced **0 false-positive alerts** in the $\ge\text{HIGH}$ severity tier (Poisson 95% upper bound: 0.868 / camera-hour).

### Q7: Can clients define custom behaviour rules without touching machine learning models?
**Answer:** Yes. The declarative rule engine parses standard JSON rule files (`configs/rules.json`). Clients can specify spatial zones, crossing directions, after-hours time windows, vehicle classes, and threat point weights without retraining any neural networks.

---

## 3. Scale, Operations & Hardware

### Q8: How many cameras can run on a single workstation or server?
**Answer:** On the reference Apple Silicon M1 (8-core CPU, 8-core GPU, 8 GB RAM), the sustained capacity boundary ($N^*$) is **8 simultaneous RTSP streams** while maintaining $<250\text{ms}$ processing latency and $<1\%$ frame drops. On an NVIDIA RTX 3080 server, capacity scales to 16–24 concurrent streams.

### Q9: Why is the platform packaged with Docker Compose instead of Kubernetes?
**Answer:** Docker Compose delivers single-command zero-friction deployability (`make quickstart`) ideal for on-premise single-server installations, perimeter substations, and edge compute boxes. Enterprise Kubernetes manifests and Helm charts are planned for multi-node clustering in v1.1.

### Q10: How does the system handle a sudden database or Redis crash?
**Answer:** The Python AI engine writes events to a local append-only journal buffer before publishing to Redis Streams. If PostgreSQL or Redis restarts, the engine continues processing video frames without crashing, flushing buffered journal records immediately upon connection recovery (Resilience Tests R1–R3).

---

## 4. Security, Privacy & Legal Compliance

### Q11: What are the licensing implications of using Ultralytics YOLOv8 for commercial clients?
**Answer:** Ultralytics YOLOv8 is distributed under GNU AGPL-3.0. For commercial deployments where source code cannot be shared under AGPL-3.0, clients must either purchase an Ultralytics enterprise commercial license, or utilize Border-AI's modular detector interface to swap in an Apache-2.0 open-source detector (ADR 0054).

### Q12: How does Border-AI protect individual privacy?
**Answer:** Facial recognition and person Re-ID are **disabled by default** and designated as consent-gated prototypes. Raw biometric embeddings are never exposed over public APIs. Searches are logged in an immutable SHA-256 hash-chained audit log, and automated retention workers purge old data according to compliance policies (ADR 0054).
