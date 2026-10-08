# Week 1 Summary: Computer Vision Foundation

**Platform:** `border-ai` (AI-Based Intelligent Video Analytics Platform for Border Surveillance)  
**Release Tag:** `v0.1-week1`  
**Milestone:** `RTSP / Video → YOLO → ByteTrack → Object ID → Zone Detection → Line Crossing → Annotated Video`

---

## 1. What Was Built (Days 1–7 Deliverables)

- **Day 1: Environment & Architecture Skeleton:** Monorepo setup (`video-ingestion`, `ai-engine`, `backend`, `frontend`), Docker Compose (PostgreSQL 16, Redis 7, MediaMTX), configuration management, Git hygiene, and safety baselines.
- **Day 2: Video Ingestion & Camera Management:** Multi-threaded camera workers, drop-oldest bounded queues for live feeds, RTSP reconnection state machine, and OpenCV file decoding with time pacing.
- **Day 3: YOLO Detection & Edge Serving:** YOLOv8 model loading, FP16/FP32 support, dynamic batch inference, detection post-processing, and FastAPI `POST /detect` endpoints.
- **Day 4: Detection Benchmarking & Hardware Profiling:** Systematic benchmarking matrix across models (yolov8n vs yolov8s), resolutions (640 vs 960), batch sizes (1 vs 3), and latency budgets.
- **Day 5: ByteTrack Multi-Object Tracking & TrackStore:** Persistent object ID assignment, Kalman state prediction, two-stage IoU association, track history buffers (`TrackStore`), ground contact anchoring, and trajectory overlays.
- **Day 6: Spatial Rule Engine (Zones & Virtual Lines):** Shapely polygon containment, line segment cross-product crossing detection, `min_track_hits` hysteresis, dwell and loitering timers, visual flash overlays, HUD event feed, and interactive click-to-draw tools (`draw_zones.py`).
- **Day 7: Full Pipeline Integration & Delivery:** Unified CLI (`scripts/run_pipeline.py`), decoupled inference and per-camera output threads, dual queue policy (backpressure offline vs drop-oldest live), HTTP MJPEG stream & snapshot API, comprehensive automated integration tests, benchmark table, and `v0.1-week1` release tag.

---

## 2. End-to-End Performance Results

Measurements on host hardware (`Apple Silicon arm64 CPU`, YOLOv8n @ 640px, FP32, target 15 FPS):

| Scenario | Cameras | Mode | Proc FPS / Camera | detect ms/frame | track ms | rules ms | render ms | write ms | Latency | Drops in / out | CPU % | RSS (MB) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Single Clip (offline) | 1 | offline | 19.9 FPS | 49.0 ms | 0.1 ms | 0.01 ms | 1.95 ms | 1.86 ms | n/a | 0 / 0 | 215% | 513 MB |
| Dual Clip (offline) | 2 | offline | 10.4 FPS | 49.9 ms | 0.1 ms | 0.01 ms | 2.50 ms | 1.90 ms | n/a | 0 / 0 | 218% | 608 MB |
| 3 Cams (live, no video) | 3 | live | 9.5 FPS | 48.9 ms | 0.1 ms | 0.01 ms | 1.40 ms | 0.00 ms | 203 ms | paced / 0 | 214% | 457 MB |
| 3 Cams (live, with video) | 3 | live | 9.1 FPS | 51.0 ms | 0.1 ms | 0.01 ms | 1.50 ms | 1.80 ms | 208 ms | paced / 0 | 218% | 476 MB |

---

## 3. What Worked Well

1. **Thread Decoupling:** Moving canvas rendering (`FrameRenderer`) and video compression (`VideoSink`) off the inference thread kept the model loop running at full speed with negligible pipeline orchestration overhead (< 1 ms).
2. **Dual Ingestion Policies:** Implementing backpressure (`put_blocking`) for offline file processing guaranteed 100% processed and rendered frames without drops, while drop-oldest eviction kept live streams bounded within ~200 ms latency.
3. **Resilient Stream Recovery:** Cold-start handling and automatic exponential reconnection logic ensured that RTSP drops never stalled or crashed other active camera channels.
4. **Structured Reproducibility:** Every run writes an isolated timestamped directory containing annotated MP4s, `events.jsonl`, `summary.json`, and an environmental `manifest.json` with commit hash and dependency versions.

---

## 4. What Was Hard & Lessons Learned

- **Video Encoding Frame Skipping:** On macOS, FFmpeg's `mpeg4` encoder occasionally fails to identify the first black frame as a keyframe, dropping packet 0 on playback. Ensuring positive coordinate scaling and verifying packet counts via `ffprobe` / `CAP_PROP_FRAME_COUNT` solved test validation discrepancies.
- **Thread Safety in Track Rendering:** Deques in `TrackStore` cannot be iterated while being modified by Kalman updates. Introducing `TrackStore.snapshot()` and `TrackView` data containers ensured complete thread isolation.
- **Hysteresis & Occlusion Edge Cases:** Rapid line oscillation and boundary hopping required a strict cooldown timer (`cooldown_s = 2.0`), direction validation, and `min_track_hits >= 3` confirmation.

---

## 5. Architectural Decision Records (ADRs)

1. [0001: Monorepo Structure and Technology Selection](decisions/0001-monorepo-structure.md)
2. [0002: Ingestion Queue Architecture and Reconnection Strategy](decisions/0002-ingestion-queues.md)
3. [0003: Detection Model Selection and Inference Runtime](decisions/0003-detection-model.md)
4. [0004: ByteTrack Multi-Camera Tracking Strategy](decisions/0004-tracking-bytetrack.md)
5. [0005: Spatial Rules Engine and Event Schema](decisions/0005-spatial-rules.md)
6. [0006: Pipeline Architecture and Stage Threading](decisions/0006-pipeline-architecture.md)

---

## 6. Known Issues

See the full [Known Issues Register](known_issues.md) for details on K1 through K8.

---

## 7. Week 2 Dependencies & Integration Touchpoints

| Week 2 Feature | What It Needs From Week 1 | Touchpoint in Codebase |
|---|---|---|
| **Day 8: ANPR & License Plate Consensus** | Stable vehicle track IDs, class tags, bounding boxes, crop images, track termination hook | `FrameTracks`, `TrackUpdate.removed`, `Track.last_bbox`, `FrameResult.frame.image` |
| **Day 9: Multi-Modal Watchlists** | Normalized event schema with `track_id`, `camera_id`, `object_class` | `Event` contract (`app/schemas/events.py`) |
| **Day 10: Face Recognition & Re-ID** | Per-track crop extractions and track embedding storage | `Track` class in `app/tracking/track_store.py` |
| **Day 11: Behaviour Analytics Engine** | Zone presence state, loitering alerts, line crossings | `RuleEngine` (`app/analytics/engine.py`) |
| **Day 12: Threat Scoring Matrix** | Structured rule metadata (`rule_type`, `dwell_s`, severity) | `Event.rule_type`, `Event.details` |
| **Day 13: Redis Event Stream Dispatch** | Single consolidated event dispatch hook | `Pipeline._emit_events()` |
| **Day 14: PostgreSQL Persistence** | Paired ENTER/EXIT events, stream flush reasons, execution manifests | `events.jsonl`, `manifest.json`, `ZoneEngine.flush()` |
