import numpy as np
import pytest

from app import config

pytestmark = pytest.mark.skipif(
    not (config.MODEL_DIR / "yolov8n.pt").exists(), reason="weights not downloaded")


@pytest.fixture(scope="module")
def detector():
    from app.detection.detector import Detector
    return Detector(model_name="yolov8n.pt", classes=["person", "car"])


def test_blank_image_has_no_detections(detector):
    assert detector.detect(np.zeros((480, 640, 3), np.uint8)) == []


def test_batch_returns_one_list_per_image(detector):
    imgs = [np.zeros((480, 640, 3), np.uint8)] * 3
    out = detector.detect_batch(imgs)
    assert len(out) == 3 and all(o == [] for o in out)


def test_empty_batch(detector):
    assert detector.detect_batch([]) == []


def test_fp16_request_is_safe_on_any_device():
    from app.detection.detector import Detector
    d = Detector(model_name="yolov8n.pt", half=True)
    assert d.half == d.device.startswith("cuda")
