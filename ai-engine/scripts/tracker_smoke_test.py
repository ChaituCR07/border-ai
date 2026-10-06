import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.detection import Detection, FrameDetections
from app.tracking.tracker import CameraTracker, TrackerParams

trk = CameraTracker("T", 30, TrackerParams(), {0: "person"})
for i in range(1, 11):
    d = Detection(0, "person", 0.9, 100 + 5 * i, 200, 140 + 5 * i, 300)
    out = trk.update(FrameDetections("T", i, float(i), 640, 480, [d]))
    print(i, [(o.track_id, round(o.x1)) for o in out])
