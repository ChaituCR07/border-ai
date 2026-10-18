import cv2
import numpy as np
import pytest

from app.identity.config import FaceConfig
from app.identity.embeddings import cosine
from app.identity.face import FaceDet, ScriptedFaceEngine, face_quality, yaw_ratio
from app.identity.reid import ColorLayoutEmbedder

LANDMARKS = np.array([[30, 40], [70, 40], [50, 60], [35, 80], [65, 80]], np.float32)
CFG = FaceConfig(min_sharpness=10.0)


def noisy(h=120, w=120):
    return np.random.default_rng(0).integers(0, 255, (h, w, 3)).astype(np.uint8)


def face(size=60, score=0.95, landmarks=LANDMARKS):
    return FaceDet(20, 20, 20 + size, 20 + size, score, landmarks)


def test_frontal_sharp_face_passes():
    q = face_quality(noisy(), face(), CFG)
    assert q.ok and q.score > 0.3 and abs(q.yaw_ratio) < 0.05


@pytest.mark.parametrize("kw, reason", [
    ({"score": 0.5}, "low_score"),
    ({"size": 20}, "too_small"),
])
def test_quality_gate_reasons(kw, reason):
    assert face_quality(noisy(), face(**kw), CFG).reason == reason


def test_profile_and_blurry_faces_are_rejected():
    turned = LANDMARKS.copy()
    turned[2] = [75, 60]                                           # nose far to one side
    assert abs(yaw_ratio(turned)) > 0.5
    assert face_quality(noisy(), face(landmarks=turned), CFG).reason == "profile"
    blurred = cv2.GaussianBlur(noisy(), (41, 41), 0)
    assert face_quality(blurred, face(), CFG).reason == "blurry"


def test_scripted_engine_cycles_embeddings_and_counts_calls():
    e1, e2 = np.eye(8)[0] + 0.01, np.eye(8)[1] + 0.01
    eng = ScriptedFaceEngine([e1, e2])
    a = eng.embed(None, eng.detect(None)[0])
    b = eng.embed(None, eng.detect(None)[0])
    assert eng.calls == 2 and cosine(a, e1) > 0.99 and cosine(b, e2) > 0.99


# ------------------------------------------------------------------ Re-ID baseline
def person_image(shirt, trousers, brightness=1.0):
    img = np.full((256, 128, 3), 90, np.uint8)                     # grey background
    img[40:140, 20:108] = shirt
    img[140:250, 25:103] = trousers
    return np.clip(img.astype(np.float32) * brightness, 0, 255).astype(np.uint8)


def test_color_layout_is_stable_and_normalized():
    emb = ColorLayoutEmbedder()
    v = emb.embed(person_image((0, 0, 200), (80, 40, 20)))
    assert v.shape == (272,) and abs(float(np.linalg.norm(v)) - 1.0) < 1e-5
    assert np.allclose(v, emb.embed(person_image((0, 0, 200), (80, 40, 20))))


def test_same_clothes_are_more_similar_than_different_clothes_even_with_lighting_change():
    emb = ColorLayoutEmbedder()
    red_a = emb.embed(person_image((0, 0, 200), (80, 40, 20)))
    red_dim = emb.embed(person_image((0, 0, 200), (80, 40, 20), brightness=0.8))
    blue = emb.embed(person_image((200, 60, 0), (30, 120, 30)))
    assert cosine(red_a, red_dim) > 0.80 and cosine(red_a, blue) < cosine(red_a, red_dim) - 0.2
