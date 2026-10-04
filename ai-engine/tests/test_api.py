import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.detect import get_detector
from app.main import app
from app.schemas.detection import Detection, FrameDetections


class FakeDetector:
    def detect_frame(self, frame, conf=None, iou=None):
        return FrameDetections(
            frame.camera_id, frame.frame_id, frame.timestamp,
            frame.image.shape[1], frame.image.shape[0],
            [Detection(0, "person", 0.91234, 10, 20, 110, 220)], 5.0)

    def detect(self, image, conf=None, iou=None):
        return [Detection(0, "person", 0.9, 10, 20, 60, 90)]

    def info(self):
        return {"model": "fake"}


@pytest.fixture
def client():
    app.dependency_overrides[get_detector] = lambda: FakeDetector()
    yield TestClient(app)          # no `with`, so the real model is not loaded
    app.dependency_overrides.clear()


def jpeg_bytes():
    ok, buf = cv2.imencode(".jpg", np.zeros((120, 160, 3), np.uint8))
    return buf.tobytes()


def test_detect_returns_contract(client):
    r = client.post("/detect?camera_id=CAM_009",
                    files={"file": ("a.jpg", jpeg_bytes(), "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert body["camera_id"] == "CAM_009"
    assert body["frame_size"] == {"width": 160, "height": 120}
    assert body["objects"][0]["class"] == "person"
    assert body["timestamp"].endswith("Z")


def test_detect_rejects_non_image(client):
    r = client.post("/detect", files={"file": ("a.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 400


def test_detect_rejects_oversized_upload(client):
    big = b"0" * (10 * 1024 * 1024 + 1)
    r = client.post("/detect", files={"file": ("a.jpg", big, "image/jpeg")})
    assert r.status_code == 413


def test_annotated_returns_jpeg(client):
    r = client.post("/detect/annotated",
                    files={"file": ("a.jpg", jpeg_bytes(), "image/jpeg")})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.headers["x-detections"] == "1"


def test_model_info(client):
    assert client.get("/model/info").json() == {"model": "fake"}
