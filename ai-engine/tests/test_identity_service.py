import json

import numpy as np
import pytest

from app.identity.config import FaceConfig, IdentityConfig, ReidConfig
from app.identity.embeddings import l2_normalize
from app.identity.face import ScriptedFaceEngine
from app.identity.gallery import FaceGallery
from app.identity.reid import PersonEmbedder
from app.identity.service import IdentityService
from app.schemas.events import REID_MATCH, WATCHLIST_MATCH
from app.schemas.tracking import FrameTracks, TrackedObject
from app.watchlist.repo import InMemoryWatchlistRepo


def vec(seed, dim=128):
    return np.random.default_rng(seed).normal(size=dim).astype(np.float32)


def near(v, noise=0.05, seed=99):
    return l2_normalize(l2_normalize(v) + noise * l2_normalize(vec(seed, len(v))))


class PixelEmbedder(PersonEmbedder):
    """Test double: the identity of a person is encoded in the crop's grey level."""
    name = "pixel"

    def __init__(self):
        self.vectors = {10: vec(1000), 20: vec(2000), 30: vec(3000)}

    def embed(self, crop):
        return l2_normalize(near(self.vectors[int(crop[0, 0, 0])], 0.02, int(crop.mean())))


FACE = dict(min_track_hits=2, every_n_frames=1, min_embeddings=3, min_sharpness=0, min_person_height_px=100,
            border_margin_px=0, review_threshold=0.5, alert_threshold=0.7, min_consistency=0.8,
            min_margin=0.05, cooldown_s=60)
REID = dict(min_track_hits=2, every_n_frames=1, min_samples=3, min_person_height_px=100, border_margin_px=0,
            similarity_threshold=0.9, max_samples_per_track=6)


def make(embeddings, enrolled=(("subject-001", 1, "HIGH"),), face_kw=None, reid_kw=None, reid=False,
         block=True, **cfg_kw):
    repo = InMemoryWatchlistRepo()
    for ident, seed, risk in enrolled:
        repo.add_face("FACE", ident, "SECRET NAME", risk, vec(seed), "scripted", actor="t")
    engine = ScriptedFaceEngine(embeddings)
    cfg = IdentityConfig(enabled=True, face=FaceConfig(engine="scripted", **{**FACE, **(face_kw or {})}),
                         reid=ReidConfig(embedder="scripted", enabled=reid, **{**REID, **(reid_kw or {})}),
                         **cfg_kw)
    hits, out = [], []
    svc = IdentityService(cfg, engine, PixelEmbedder() if reid else None,
                          FaceGallery(repo, "scripted"), hit_recorder=hits.append)
    svc.attach(emit=lambda cid, ev: out.extend(ev), block_when_full=block)
    svc.face_gallery.reload()
    return svc, repo, out, hits, engine


IMG = np.full((240, 320, 3), 10, np.uint8)                     # grey level 10 = "person 10"


def frame(i, tracks=((1, (100, 20, 200, 200)),), cam="CAM", label="person"):
    objs = []
    for tid, bbox in tracks:
        o = TrackedObject(tid, 0, label, 0.9, *bbox)
        objs.append(o)
    return FrameTracks(cam, i, float(i), 320, 240, objs)


def feed(svc, n, start=1, image=IMG, **kw):
    for i in range(start, start + n):
        svc.submit(kw.get("cam", "CAM"), frame(i, **kw), image)
        svc.run_pending()


# ------------------------------------------------------------------ face path
def test_enrolled_person_produces_a_review_event_without_a_name():
    svc, repo, out, hits, _ = make([near(vec(1))])
    feed(svc, 8)
    assert len(out) == 1
    e = out[0]
    assert e.type == WATCHLIST_MATCH and e.details["match_basis"] == "face"
    assert e.details["status"] == "review" and e.details["review_required"] is True
    assert e.details["similarity"] > 0.9 and e.details["embeddings"] >= 3 and e.details["risk_level"] == "HIGH"
    blob = json.dumps(e.to_dict())
    assert "SECRET NAME" not in blob and "embedding\":" not in blob.replace("embedding_model", "")
    assert svc.flags_snapshot("CAM") == {1: "HIGH REVIEW FACE"}
    assert [h.match_basis for h in hits] == ["face"] and hits[0].plate is None and hits[0].similarity > 0.9


def test_a_stranger_is_not_matched():
    svc, _, out, hits, _ = make([vec(555)])
    feed(svc, 10)
    assert out == [] and hits == [] and svc.stats["face_no_match_below_threshold"] >= 1


def test_face_matches_never_alert_unless_explicitly_allowed():
    svc, _, out, _, _ = make([near(vec(1))])
    feed(svc, 8)
    assert out[0].details["status"] == "review"
    svc2, _, out2, _, _ = make([near(vec(1))], face_kw={"allow_alert": True})
    feed(svc2, 8)
    assert out2[0].details["status"] == "alert"


def test_ambiguous_matches_are_rejected():
    svc, _, out, _, _ = make([near(vec(1), 0.02)],
                             enrolled=(("subject-001", 1, "HIGH"), ("subject-002", 1, "HIGH")))
    # two entries with the SAME vector: the margin is zero
    feed(svc, 8)
    assert out == [] and svc.stats["face_no_match_ambiguous"] >= 1


def test_a_track_mixing_two_people_is_not_matched():
    """Alternating faces of two different people (a tracker ID switch) must not match either."""
    svc, _, out, _, _ = make([near(vec(1)), vec(777)] * 3, face_kw={"min_consistency": 0.9})
    feed(svc, 10)
    assert out == [] and svc.stats["face_no_match_inconsistent"] >= 1


def test_poor_faces_are_skipped_before_embedding():
    svc, _, out, _, engine = make([near(vec(1))], face_kw={"min_face_px": 500})     # every face is "too small"
    feed(svc, 6)
    assert out == [] and svc.stats["face_skipped_too_small"] >= 1 and svc.stats["face_embeddings"] == 0


def test_scheduling_respects_height_border_class_and_read_cap():
    svc, _, _, _, engine = make([near(vec(1))], face_kw={"max_reads_per_track": 3, "min_embeddings": 99})
    feed(svc, 20)
    assert engine.calls == 3                                                     # read cap
    svc2, _, _, _, engine2 = make([near(vec(1))])
    feed(svc2, 6, tracks=((1, (100, 20, 200, 80)),))                             # only 60 px tall
    feed(svc2, 6, label="car")
    assert engine2.calls == 0


def test_the_largest_persons_get_the_jobs_when_over_the_per_frame_cap():
    svc, *_ = make([near(vec(1))], max_jobs_per_frame=1)
    tracks = ((1, (10, 20, 60, 130)), (2, (100, 20, 220, 200)))                  # track 2 is much bigger
    for i in range(1, 4):
        svc.submit("CAM", frame(i, tracks=tracks), IMG)
        assert svc._q.qsize() <= 1
        svc.run_pending()
    assert svc._states[("CAM", 2)].face_scheduled >= 1 and svc._states[("CAM", 1)].face_scheduled == 0


def test_the_face_search_stops_after_a_match_and_cooldown_limits_repeats():
    svc, _, out, hits, engine = make([near(vec(1))])
    feed(svc, 6)
    calls_after_match = engine.calls
    feed(svc, 10, start=7)
    assert engine.calls == calls_after_match                                     # face_done: no more work
    feed(svc, 8, tracks=((2, (100, 20, 200, 200)),), start=30)                   # another track, same person, within 60 s
    assert len(out) == 1 and svc.stats["face_suppressed"] == 1
    assert [h.status for h in hits] == ["review", "suppressed"]


def test_tracks_are_cleaned_up_and_flags_cleared_when_they_end():
    svc, _, out, _, _ = make([near(vec(1))])
    feed(svc, 6)
    assert svc.flags_snapshot("CAM") and svc.status()["active_persons"] == 1
    svc.on_tracks_removed("CAM", [TrackedObject(1, 0, "person", 0.9, 0, 0, 1, 1)])
    assert svc.flags_snapshot("CAM") == {} and svc.status()["active_persons"] == 0


def test_finalization_waits_for_queued_jobs():
    svc, _, out, _, _ = make([near(vec(1))])
    for i in range(1, 8):
        svc.submit("CAM", frame(i), IMG)                                         # queued, not processed
    svc.on_tracks_removed("CAM", [TrackedObject(1, 0, "person", 0.9, 0, 0, 1, 1)])
    assert svc.status()["active_persons"] == 1                                   # still waiting for jobs
    svc.run_pending()
    assert svc.status()["active_persons"] == 0


def test_live_mode_drops_the_oldest_jobs_and_keeps_counts_consistent():
    svc, *_ = make([near(vec(1))], block=False, queue_size=2)
    for i in range(1, 9):
        svc.submit("CAM", frame(i), IMG)
    assert svc.stats["dropped"] >= 1
    svc.run_pending()
    assert svc._states[("CAM", 1)].pending == 0


def test_worker_thread_runs_and_stops_cleanly():
    svc, _, out, _, _ = make([near(vec(1))])
    svc.start()
    for i in range(1, 9):
        svc.submit("CAM", frame(i), IMG)
    svc.stop(drain=True)
    assert len(out) == 1
    svc.stop(drain=True)


def test_the_database_outage_does_not_stop_matching():
    svc, repo, out, _, _ = make([near(vec(1))])
    repo.fail = True                                                              # gallery keeps the loaded matrix
    feed(svc, 8)
    assert len(out) == 1


# ------------------------------------------------------------------ Re-ID path
def test_the_same_appearance_on_another_camera_becomes_a_reid_candidate():
    svc, _, out, _, _ = make([vec(555)], reid=True)
    feed(svc, 8, cam="A")                                                         # person 10 on camera A
    svc.on_tracks_removed("A", [TrackedObject(1, 0, "person", 0.9, 0, 0, 1, 1)])
    assert svc.status()["reid_gallery"] == 1
    for i in range(100, 108):
        svc.submit("B", frame(i, tracks=((7, (100, 20, 200, 200)),), cam="B"), IMG)
        svc.run_pending()
    reid = [e for e in out if e.type == REID_MATCH]
    assert len(reid) == 1
    d = reid[0].details
    assert d["status"] == "candidate" and d["review_required"] is True
    assert d["candidates"][0]["camera_id"] == "A" and d["candidates"][0]["track_id"] == 1
    assert svc.labels_snapshot("B") == {7: "= A #1?"}


def test_a_different_appearance_or_the_same_camera_gives_no_candidate():
    svc, _, out, _, _ = make([vec(555)], reid=True)
    feed(svc, 8, cam="A")
    svc.on_tracks_removed("A", [TrackedObject(1, 0, "person", 0.9, 0, 0, 1, 1)])
    other = np.full((240, 320, 3), 20, np.uint8)                                  # "person 20"
    for i in range(100, 108):
        svc.submit("B", frame(i, tracks=((7, (100, 20, 200, 200)),), cam="B"), other)
        svc.run_pending()
    for i in range(200, 208):                                                     # same person, same camera
        svc.submit("A", frame(i, tracks=((9, (100, 20, 200, 200)),), cam="A"), IMG)
        svc.run_pending()
    assert [e for e in out if e.type == REID_MATCH] == []


def test_reid_events_contain_no_images_or_embeddings():
    svc, _, out, _, _ = make([vec(555)], reid=True)
    feed(svc, 8, cam="A")
    svc.on_tracks_removed("A", [TrackedObject(1, 0, "person", 0.9, 0, 0, 1, 1)])
    for i in range(100, 108):
        svc.submit("B", frame(i, tracks=((7, (100, 20, 200, 200)),), cam="B"), IMG)
        svc.run_pending()
    blob = json.dumps([e.to_dict() for e in out if e.type == REID_MATCH])
    assert "[" not in json.dumps(out[0].to_dict()["details"].get("embedding", "")) and len(blob) < 2000


# ------------------------------------------------------------------ safeguards
def test_identity_is_disabled_by_default_and_saves_no_images():
    cfg = IdentityConfig.from_config({})
    assert cfg.enabled is False and cfg.save_crops is False and cfg.face.allow_alert is False
