import numpy as np
import pytest

from app.identity.config import FaceConfig
from app.identity.embeddings import cosine, l2_normalize
from app.identity.enroll import ConsentRequired, enroll_subject
from app.identity.face import ScriptedFaceEngine
from app.watchlist.models import InvalidEntry
from app.watchlist.repo import InMemoryWatchlistRepo

CFG = FaceConfig(min_sharpness=0)
IMAGES = [np.zeros((120, 120, 3), np.uint8)] * 5


def vec(seed, dim=128):
    return np.random.default_rng(seed).normal(size=dim).astype(np.float32)


def same_person(n=5):
    base = l2_normalize(vec(1))
    return [l2_normalize(base + 0.05 * l2_normalize(vec(10 + i))) for i in range(n)]


def test_enrollment_requires_explicit_consent():
    repo = InMemoryWatchlistRepo()
    with pytest.raises(ConsentRequired):
        enroll_subject(repo, ScriptedFaceEngine(same_person()), IMAGES, "subject-001", "A", "LOW", CFG,
                       consent_confirmed=False)
    assert repo.list_entries() == []


def test_enrollment_stores_only_the_combined_embedding():
    repo = InMemoryWatchlistRepo()
    engine = ScriptedFaceEngine(same_person())
    result = enroll_subject(repo, engine, IMAGES, "subject-001", "A", "LOW", CFG,
                            consent_confirmed=True, actor="alice")
    assert result.used == 5 and result.consistency > 0.9
    stored = repo.load_face_embeddings(engine.model_name)
    assert len(stored) == 1 and cosine(stored[0][1], vec(1)) > 0.95
    assert repo.audit_log()[0]["actor"] == "alice"


def test_enrollment_needs_enough_usable_photos():
    with pytest.raises(InvalidEntry):
        enroll_subject(InMemoryWatchlistRepo(), ScriptedFaceEngine(same_person(2)), IMAGES[:2],
                       "subject-001", "A", "LOW", CFG, consent_confirmed=True)


def test_enrollment_refuses_photos_of_different_people():
    mixed = [vec(1), vec(2), vec(3), vec(4), vec(5)]
    with pytest.raises(InvalidEntry):
        enroll_subject(InMemoryWatchlistRepo(), ScriptedFaceEngine(mixed), IMAGES,
                       "subject-001", "A", "LOW", CFG, consent_confirmed=True)
