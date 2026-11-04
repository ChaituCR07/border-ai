# Week 4 Integration Backlog (Days 22–28)

Open non-blocking items and optimizations triaged from Week 3 integration and scheduled for Week 4.

## Day 22: Detection & Tracking Evaluation (Completed)
- [x] Evaluated detection mAP, P/R/F1, and foot-point error across COCO-1000, BDD100K, and CCTV fixtures with 95% bootstrap CIs (ADRs 0035, 0036).
- [x] Assessed tracker continuity, ID switches, and false tracks on MOT17 static CCTV sequences with dev-split tuning policy (ADR 0037).
- [x] Quantified tracking impact on downstream security alerts (96.2% event recall, 2.8% double-counted alerts).
- [x] Created CCTV mini-fixture and automated CI regression test (`tests/test_model_regression.py`).

## Day 23: ANPR Model & Dataset Benchmarks (Upcoming)
- [ ] Benchmark ANPR consensus character accuracy (Levenshtein distance, exact match rate) on Indian plate layout splits.
- [ ] Evaluate character-level substitution confusion matrix for look-alike characters (`B/8`, `O/0`, `1/I`, `S/5`, `Z/2`).
- [ ] Measure multi-frame consensus convergence latency (frames to stable plate candidate).
- [ ] Quantify low-light, angle-distortion, and motion-blur degradation boundaries.

## Day 24: High-Density Performance & Hardware Benchmarks
- [ ] Benchmark multi-camera scaling (1, 2, 4, 8 streams) on GPU and Apple Silicon MPS.
- [ ] Profile memory usage and VRAM steady state over 4+ hours continuous streaming.

## Day 25: False-Positive Matrix
- [ ] Run 6 standard false-positive edge cases using the Day 21 scenario harness.
- [ ] Validate non-violation turns and permissible direction traversals.

## Day 26: Security & Authentication Hardening
- [ ] Integrate JWT authentication and role-based access control (Admin, Operator, Investigator, Viewer).
- [ ] Enforce WebSocket connection authentication tickets.

## Day 27: Full Docker Compose Containerization
- [ ] Package engine, backend, frontend, and Nginx reverse proxy into unified Compose.

## Day 28: Final Polish & Showcase Demo
- [ ] Final end-to-end rehearsal recording and production documentation freeze.
