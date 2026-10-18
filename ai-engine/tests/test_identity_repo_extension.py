from datetime import datetime, timezone

import numpy as np
import pytest

from app.watchlist.models import DuplicateEntry, InvalidEntry, WatchlistHit


def vec(seed, dim=128):
    return np.random.default_rng(seed).normal(size=dim).astype(np.float32)


def test_add_face_and_load_by_model(repo):
    e = repo.add_face("FACE", "subject-001", "Volunteer A", "LOW", vec(1), "model-a", count=5, actor="t")
    assert e.entity_type == "FACE" and e.normalized_identifier == "subject-001"
    loaded = repo.load_face_embeddings("model-a")
    assert [x.watchlist_id for x, _ in loaded] == [e.watchlist_id]
    v = loaded[0][1]
    assert v.shape == (128,) and abs(float(np.linalg.norm(v)) - 1.0) < 1e-5
    assert float(np.dot(v, vec(1) / np.linalg.norm(vec(1)))) > 0.9999
    assert repo.load_face_embeddings("model-b") == []                     # never mix embedding models


def test_deactivated_faces_are_not_loaded(repo):
    e = repo.add_face("FACE", "subject-001", "A", "LOW", vec(1), "m")
    repo.deactivate(e.watchlist_id)
    assert repo.load_face_embeddings("m") == []


def test_face_entries_reject_bad_input(repo):
    with pytest.raises(InvalidEntry):
        repo.add_face("VEHICLE", "KA01AB1234", "x", "LOW", vec(1), "m")            # wrong type
    with pytest.raises(InvalidEntry):
        repo.add_face("FACE", "subject-002", "x", "LOW", np.zeros(128), "m")       # zero vector
    with pytest.raises(InvalidEntry):
        repo.add_face("FACE", "subject-002", "x", "LOW", np.full(128, np.nan), "m")
    with pytest.raises(InvalidEntry):
        repo.add_face("FACE", "subject-002", "x", "LOW", vec(1, dim=8), "m")       # too short


def test_duplicate_face_identifier_is_rejected(repo):
    repo.add_face("FACE", "subject-001", "A", "LOW", vec(1), "m")
    with pytest.raises(DuplicateEntry):
        repo.add_face("FACE", "SUBJECT-001", "B", "LOW", vec(2), "m")


def test_listing_never_exposes_embeddings(repo):
    repo.add_face("FACE", "subject-001", "A", "LOW", vec(1), "m")
    entry = repo.list_entries(entity_types=["FACE"])[0]
    assert not hasattr(entry, "embedding")


def test_audit_records_enrollment_without_the_vector(repo):
    repo.add_face("FACE", "subject-001", "A", "LOW", vec(1), "m", actor="alice")
    row = repo.audit_log()[0]
    assert row["action"] == "ADD" and row["actor"] == "alice"
    assert "embedding" not in str(row["details"]).replace("embedding_model", "").replace("embedding_dim", "")


def test_face_hits_are_stored_with_their_basis(repo):
    e = repo.add_face("FACE", "subject-001", "A", "LOW", vec(1), "m")
    repo.record_hit(WatchlistHit(watchlist_id=e.watchlist_id, camera_id="CAM", track_id=3, plate=None,
                                 match_type="face", distance=0.2, plate_confidence=None, score=72,
                                 status="review", seen_at=datetime.now(timezone.utc), event_id="x",
                                 match_basis="face", similarity=0.8))
    row = repo.recent_hits()[0]
    assert row["match_basis"] == "face" and row["plate"] is None and row["similarity"] == pytest.approx(0.8, abs=1e-6)
