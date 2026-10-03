# Platform Benchmarks

## Object Detection & Inference Performance

| Date | Hardware | Model | Input Size | Cameras | ms/frame (mean) | FPS | Notes |
|---|---|---|---|---|---|---|---|
| 2026-10-03 | Apple Silicon / CPU | YOLOv8n | 640x640 | 1 | 40.1 ms | 24.9 FPS | Single stream fast decode baseline |
| 2026-10-03 | Apple Silicon / CPU | YOLOv8n | 640x640 | 3 | 41.5 ms | 8.6 FPS/cam | Sequential multi-stream round-robin |
| 2026-10-03 | Apple Silicon / CPU | YOLOv8n | 960x960 | 1 | 110.3 ms | 9.1 FPS | High-res distant object test |
