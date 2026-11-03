# Test Footage Manifest

Manifest of video clips used for full-system integration and acceptance testing.

| Clip Path | Camera ID | Duration | Scenario / Role | Source / Permitted Rights |
|---|---|---|---|---|
| `footage/camera_01/normal.mp4` | CAM-01 | 45s | S0 (Negative Control) | Synthetic CCTV pipeline generator (Apache 2.0) |
| `footage/camera_01/restricted_zone.mp4` | CAM-01 | 60s | S1 (Perimeter Intrusion) | Controlled test staging (Border-AI project owned) |
| `footage/camera_02/watchlist.mp4` | CAM-02 | 45s | S2 (Watchlist KA01AB1234) | Controlled synthetic test vehicle with plate overlay |
| `footage/camera_04/journey_cam04.mp4` | CAM-04 | 45s | S3 (Cross-Camera Correlated) | Multi-camera correlated sequence KA01AB1234 |

> Note: All test clips represent controlled or synthetic footage created for pipeline verification. Model benchmark datasets are evaluated independently in Days 22–23.
