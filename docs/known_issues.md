# Known Issues Register

| ID | Area | Description | Severity | Status | Workaround / Plan |
|---|---|---|---|---|---|
| K1 | Tracking | ID switches when people cross paths in dense scenes | Medium | Known | Tuned `match_thresh`; appearance Re-ID in Week 2 |
| K2 | Tracking | New ID assigned after occlusion exceeding the lost-track buffer | Medium | Known | Increase `track_buffer`; multi-camera Re-ID in Week 2 |
| K3 | Detection | Lower recall on low-light / IR footage and distant small objects | Medium | Known | Increase `imgsz` to 960px or apply CLAHE preprocessing; fine-tuning model in later phases |
| K4 | Rules | Boundary ID switch may trigger extra `spawned_inside` or missed crossing | Low | Known | Require `min_track_hits >= 3` and use line hysteresis |
| K5 | Pipeline | Live MP4 encoding assumes configured target FPS even if ingestion drops occur | Low | Known | Use `--no-video` for long live runs, or record at dynamically measured FPS |
| K6 | Ingestion | RTSP validated against MediaMTX / RTSP simulator | Medium | Known | Field validation on physical IP camera prior to hardware pilot |
| K7 | API | MJPEG and status API endpoints do not enforce authentication | Medium | Known | Bound strictly to `127.0.0.1`; JWT/RBAC planned for Week 3-4 |
| K8 | Ingestion | Disparate camera resolutions resized at edge rather than source capture | Low | Known | Standardize `resize_width=1280` in `cameras.json` |

## Severity Classification
- **High:** Incorrect/lost security events, service crashes, data corruption.
- **Medium:** Degraded tracking or detection precision under challenging edge cases.
- **Low:** Cosmetic timing variations or minor edge-case artifacts.
