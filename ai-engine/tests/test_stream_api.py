import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.stream import mjpeg_chunks
from app.main import app
from app.pipeline.sinks import FrameHub


class FakeEvents:
    def recent_records(self, limit=50, camera_id=None):
        return [{"camera_id": "C1", "type": "ZONE_ENTER"}][:limit]


class FakePipeline:
    camera_ids = ["C1"]
    stopped = False

    def __init__(self):
        self.hub = FrameHub()
        self.events = FakeEvents()

    def status(self):
        return {"state": "running"}


@pytest.fixture
def fake():
    p = FakePipeline()
    app.state.pipeline = p
    yield p
    delattr(app.state, "pipeline")


def test_status_and_events(fake):
    c = TestClient(app)
    assert c.get("/pipeline/status").json() == {"state": "running"}
    assert c.get("/events/recent?limit=5").json()["events"][0]["type"] == "ZONE_ENTER"


def test_snapshot_before_and_after_a_frame(fake):
    c = TestClient(app)
    assert c.get("/snapshot/C1").status_code == 404
    fake.hub.put("C1", np.zeros((48, 64, 3), np.uint8))
    r = c.get("/snapshot/C1")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"


def test_unknown_camera_is_404(fake):
    assert TestClient(app).get("/snapshot/NOPE").status_code == 404
    assert TestClient(app).get("/stream/NOPE").status_code == 404


def test_503_when_pipeline_is_not_running():
    assert TestClient(app).get("/pipeline/status").status_code == 503


def test_mjpeg_chunk_format(fake):
    fake.hub.put("C1", np.zeros((48, 64, 3), np.uint8))
    gen = mjpeg_chunks(fake, "C1")
    chunk = next(gen)
    assert chunk.startswith(b"--frame\r\nContent-Type: image/jpeg")
    assert b"\xff\xd8" in chunk
    fake.stopped = True
    gen.close()
