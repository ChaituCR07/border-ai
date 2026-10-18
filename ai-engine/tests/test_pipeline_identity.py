import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.analytics.engine import RuleEngine
from app.identity.config import FaceConfig, IdentityConfig, ReidConfig
from app.identity.face import ScriptedFaceEngine
from app.identity.gallery import FaceGallery
from app.identity.service import IdentityService
from app.pipeline.pipeline import Pipeline
from app.schemas.detection import Detection, FrameDetections
from app.tracking.tracker import TrackerParams
from app.watchlist.config import WatchlistConfig
from app.watchlist.repo import InMemoryWatchlistRepo
from app.watchlist.service import WatchlistService
from ingestion.camera_manager import CameraManager
from ingestion.sources.file_source import FileSource


def vec(seed, dim=128):
    return np.random.default_rng(seed).normal(size=dim).astype(np.float32)


class FakePersonDetector:
    model = SimpleNamespace(names={0: "person"})

    def detect_frames(self, frames, conf=None, iou=None):
        return [FrameDetections(f.camera_id, f.frame_id, f.timestamp, f.image.shape[1], f.image.shape[0],
                                [Detection(0, "person", 0.9, 100, 20, 200, 200)], 1.0) for f in frames]

    def info(self):
        return {"model": "fake"}


@pytest.fixture
def sample_video(tmp_path):
    path = tmp_path / "person.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
    for i in range(60):
        w.write(np.full((240, 320, 3), (i * 3) % 255, np.uint8))
    w.release()
    return path


def identity_for(face_vec, repo, enabled=True):
    cfg = IdentityConfig(
        enabled=enabled,
        face=FaceConfig(engine="scripted", min_track_hits=3, every_n_frames=2, min_embeddings=3,
                        min_sharpness=0, min_person_height_px=100, border_margin_px=0,
                        review_threshold=0.5, alert_threshold=0.7, min_consistency=0.8),
        reid=ReidConfig(embedder="scripted", enabled=False))
    engine = ScriptedFaceEngine([face_vec])
    wl = WatchlistService(repo, WatchlistConfig())
    return IdentityService(cfg, engine, None, FaceGallery(repo, "scripted"), hit_recorder=wl.persist_hit), wl, engine


def run(tmp_path, sample_video, face_vec, repo):
    ident, wl, engine = identity_for(face_vec, repo)
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakePersonDetector(), mgr, TrackerParams(), RuleEngine(tmp_path / "zones"),
                 tmp_path / "runs", watchlist=wl, identity=ident)
    p.start()
    assert p.join(timeout=60)
    events = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    return p, events, engine


@pytest.mark.integration
def test_enrolled_face_raises_a_review_event_and_a_stored_hit(tmp_path, sample_video):
    repo = InMemoryWatchlistRepo()
    repo.add_face("FACE", "subject-001", "SECRET NAME", "HIGH", vec(1), "scripted", actor="t")
    probe = vec(1) + 0.05 * vec(2)
    p, events, _ = run(tmp_path, sample_video, probe, repo)
    matches = [e for e in events if e["type"] == "WATCHLIST_MATCH" and e["details"]["match_basis"] == "face"]
    assert len(matches) == 1
    assert matches[0]["details"]["status"] == "review" and matches[0]["score"] >= 50
    assert "SECRET NAME" not in json.dumps(matches[0])
    hits = repo.recent_hits()
    assert len(hits) == 1 and hits[0]["match_basis"] == "face"
    assert p.status()["identity"]["face_reviews"] == 1


@pytest.mark.integration
def test_a_different_face_raises_nothing(tmp_path, sample_video):
    repo = InMemoryWatchlistRepo()
    repo.add_face("FACE", "subject-001", "A", "HIGH", vec(1), "scripted", actor="t")
    p, events, _ = run(tmp_path, sample_video, vec(999), repo)
    assert [e for e in events if e["type"] == "WATCHLIST_MATCH"] == [] and repo.recent_hits() == []


@pytest.mark.integration
def test_identity_features_do_nothing_unless_enabled(tmp_path, sample_video):
    repo = InMemoryWatchlistRepo()
    repo.add_face("FACE", "subject-001", "A", "HIGH", vec(1), "scripted", actor="t")
    mgr = CameraManager([FileSource("CAM_T", sample_video, realtime=False)])
    p = Pipeline(FakePersonDetector(), mgr, TrackerParams(), RuleEngine(tmp_path / "zones"),
                 tmp_path / "runs", identity=None)                 # what build_identity returns when disabled
    p.start()
    assert p.join(timeout=60)
    assert p.status()["identity"] is None
    events = [json.loads(l) for l in (p.run_dir / "events.jsonl").read_text().splitlines()]
    assert all(e["type"] != "WATCHLIST_MATCH" for e in events)
