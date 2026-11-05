# Week 4 Integration Backlog (Days 22–28)

Open non-blocking items and optimizations triaged from Week 3 integration and scheduled for Week 4.

## Day 22: Detection & Tracking Evaluation (Completed)
- [x] Evaluated detection mAP, P/R/F1, and foot-point error across COCO-1000, BDD100K, and CCTV fixtures with 95% bootstrap CIs (ADRs 0035, 0036).
- [x] Assessed tracker continuity, ID switches, and false tracks on MOT17 static CCTV sequences with dev-split tuning policy (ADR 0037).
- [x] Quantified tracking impact on downstream security alerts (96.2% event recall, 2.8% double-counted alerts).
- [x] Created CCTV mini-fixture and automated CI regression test (`tests/test_model_regression.py`).

## Day 23: ANPR Model & Dataset Benchmarks (Completed)
- [x] Evaluated ANPR consensus character accuracy (Levenshtein distance, exact match rate) on Indian plate layout splits (`run-20261105-anpr-m3`, ADR 0038).
- [x] Analyzed character-level substitution confusion matrix for look-alike characters (`B/8`, `O/0`, `1/I`, `S/5`, `Z/2`) and audited ADR 0039 schema policy.
- [x] Measured multi-frame consensus convergence latency (5.4 frames/vehicle, 64.8% OCR calls saved with early stopping).
- [x] Quantified low-light, angle-distortion, and plate-height degradation boundaries (derived minimum plate height $\ge 30\,\text{px}$ rule).
- [x] Formulated consolidated model cards (`docs/model_eval/model_cards/`) and camera placement guidance (`docs/guides/anpr_camera_guidance.md`).
- [x] Created CI regression baseline gate (`evaluation/fixtures/anpr_synth/baseline.json`) and claims compliance checker (`scripts/report/check_claims.py`).

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
