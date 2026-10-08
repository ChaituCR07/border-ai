# 0006. Pipeline Architecture and Stage Threading

## Context
Week 1 integrates video ingestion, YOLOv8 object detection, ByteTrack multi-object tracking, and spatial rule engines into a unified runtime pipeline. A naive single-threaded pipeline is bottlenecked by OpenCV drawing and video encoding (~4-6 ms/frame), reducing inference throughput by 10-15%. Conversely, parallelizing tracking or inference across threads introduces race conditions and non-deterministic frame ordering.

## Decisions

1. **Single Inference Thread for Detection, Tracking, and Rules:**
   YOLO batched inference, per-camera ByteTrack updates, and rule evaluation execute strictly in series on one thread. This guarantees sequential frame ordering per camera and prevents concurrent access to non-thread-safe model weights and tracker states.

2. **Decoupled Output Threads (One Per Camera):**
   Canvas overlay drawing (`FrameRenderer`) and MP4 video encoding (`VideoSink`) run on dedicated per-camera daemon threads. This offloads CPU-bound drawing from GPU/CPU inference, maintaining maximum model saturation.

3. **Dual Queue Policy by Operating Mode:**
   - **Offline Mode (Files):** Ingestion and output queues use backpressure (`put_blocking`). Ingest blocks when downstream queues fill, guaranteeing zero dropped frames and full analytical reproducibility.
   - **Live Mode (RTSP & Paced Streams):** Queues use drop-oldest eviction (`put_drop_oldest`). Latency stays bounded (~200 ms), and frame drops are tracked and reported.

4. **One Frame Per Camera Per Inference Cycle:**
   Dynamic batches collect at most one frame per active camera per inference cycle. This enforces balanced latency across all camera feeds and prevents any single camera from dominating the batch.

5. **Immutable State Snapshots for Rendering:**
   The inference thread creates an immutable `StoreSnapshot` containing decoupled `TrackView` copies. The renderer reads the snapshot without mutating or racing live `TrackStore` deques.

6. **Immediate Event Emission:**
   Events are written synchronously to `events.jsonl` on the inference thread immediately upon trigger. Even if video frames are dropped in live mode, no security events are ever lost.

7. **Synchronized Clock Abstraction:**
   Offline processing maps frame timestamps from video elapsed time (`video_time_ms`) onto a real wall-clock epoch, ensuring realistic durations. Live processing uses wall-clock timestamps.

8. **Deterministic Run Output Directories:**
   Every execution creates an isolated directory `outputs/runs/<run_id>/` containing:
   - `annotated_<camera_id>.mp4`
   - `events.jsonl` (and optional `tracks.jsonl`)
   - `summary.json` (aggregate timings, drop counts, event counters)
   - `manifest.json` (git commit, library versions, hardware metadata, active configurations)

9. **Fail-Fast Startup Validation:**
   Zone rules and camera configurations are parsed and validated before threads spawn. Configuration errors halt execution immediately with actionable diagnostics.

10. **Localhost API Binding:**
    MJPEG streaming (`/stream/{camera}`) and snapshot endpoints bind strictly to loopback `127.0.0.1` without external authentication, pending the Week 3-4 security layer.

## Consequences
- Throughput matches standalone model benchmarks with less than 1 ms pipeline orchestration overhead.
- Total zero frame drops in benchmark/offline mode.
- Resilient stream recovery when RTSP connections drop or restore.
