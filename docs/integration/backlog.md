# Week 4 Integration Backlog (Days 22–28)

Open non-blocking items and optimizations triaged from Week 3 integration and scheduled for Week 4.

## Day 22–23: Model & Dataset Benchmarks
- [ ] Evaluate detection mAP and recall across real BDD100K and MOT17 datasets.
- [ ] Benchmark ANPR consensus character accuracy on full Indian plate test splits.
- [ ] Assess tracker fragmentation and ID switch rates under heavy occlusions.

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
