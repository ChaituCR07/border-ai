from app.schemas.detection import Detection, FrameDetections
from app.utils.timeutil import to_iso_utc


def test_iso_timestamp_is_utc_with_z():
    ts = to_iso_utc(1_700_000_000.123)
    assert ts.startswith("2023-11-14T22:13:20")
    assert ts.endswith("Z")


def test_frame_detections_to_dict_contract():
    fd = FrameDetections(
        camera_id="CAM_001", frame_id=7, timestamp=1_700_000_000.0,
        width=1280, height=720,
        detections=[Detection(0, "person", 0.91234, 10.04, 20.0, 110.0, 220.0)],
        inference_ms=5.123)
    d = fd.to_dict()
    assert d["camera_id"] == "CAM_001" and d["frame_id"] == 7
    assert d["frame_size"] == {"width": 1280, "height": 720}
    assert d["inference_ms"] == 5.12
    obj = d["objects"][0]
    assert obj["class"] == "person" and obj["class_id"] == 0
    assert obj["confidence"] == 0.912
    assert obj["bbox"] == [10.0, 20.0, 110.0, 220.0]
