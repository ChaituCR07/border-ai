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
| K9 | ANPR | Distant or low-resolution vehicle plates (< 50px width) unreadable | Medium | Known | Skip small vehicles with `min_vehicle_width_px: 90`; quality gate rejects blurry frames |
| K10 | ANPR | Tracker ID switch splits one vehicle's OCR consensus into two records | Low | Known | Merged via Watchlist and multi-camera plate deduplication in Day 9 |
| K11 | ANPR | Severe camera angles (> 35 degrees) and headlight glare degrade character segmentation | Medium | Known | Camera placement guidelines, CLAHE preprocessing, and consensus voting across frames |
| K12 | Watchlist | Tracker ID switch splits one vehicle into two tracks (two lookups) | Low | Mitigated | Cooldown suppresses duplicate alert within 60s; hits are stored |
| K13 | Watchlist | OCR-tolerant near matches risk false matches on visually similar plates | Medium | Mitigated | Near matches default to review status requiring human confirmation |
| K14 | Watchlist | Face and Person entity embeddings are stored but matching is not executed | Low | Resolved | Implemented in Day 10 with FaceGallery, SFace, and consent gating |
| K15 | Identity | Face matching accuracy drops significantly on steep-angle or low-light CCTV | Medium | Mitigated | Quality gate skips blurry/turned faces; matches are review-only by default |
| K16 | Identity | Pedestrian ID switch may contaminate a track's face embedding | Medium | Mitigated | Multi-frame consistency threshold (>= 0.75) detects and rejects mixed tracks |
| K17 | Re-ID | Color-layout baseline Re-ID confuses people wearing similar dark clothing | Medium | Mitigated | Candidates are flagged with '= CAM_XXX #YY?' and require human confirmation |
| K18 | Behaviour | Tracker ID switch resets zone dwell time counter | Low | Known | High track buffer mitigates; tune `min_dwell_s` threshold |
| K19 | Behaviour | Rules depending on asynchronous plate/watchlist events fire a few frames apart between runs | Low | Known | Compare event sets rather than exact frame numbers; deterministic for R001-R004 |
| K20 | Behaviour | Weekday filters on windows past midnight use local date of evaluation | Low | Documented | Avoid weekday constraints on wrapped midnight windows or account for morning rollover |
| K21 | Threat | People tracks lack persistent biometric identity across tracker ID swaps | Medium | Known | Plate merging handles vehicles; Re-ID provides review candidates only |
| K22 | Threat | Asynchronous evidence (ANPR/Face) may arrive a few frames after track birth | Low | Known | Window evaluation absorbs and updates threat score as evidence resolves |
| K23 | Threat | Scoring weights and thresholds are design selections | Low | Mitigated | Fully configurable via rules.json scoring section; documented in threat_scoring.md |

## Severity Classification
- **High:** Incorrect/lost security events, service crashes, data corruption.
- **Medium:** Degraded tracking or detection precision under challenging edge cases.
- **Low:** Cosmetic timing variations or minor edge-case artifacts.
