import numpy as np
import pytest

from app.identity.aggregate import EmbeddingAggregator
from app.identity.config import FaceConfig, IdentityConfig, ReidConfig
from app.identity.decision import decide_face_match, similarity_score
from app.identity.embeddings import cosine, from_bytes, l2_normalize, to_bytes, validate_embedding
from app.identity.gallery import FaceGallery, ReidGallery, ReidItem
from app.identity.metrics import (equal_error_rate, expected_false_matches, pair_similarities,
                                  rank_k_accuracy, threshold_for_far, threshold_table)
from app.watchlist.repo import InMemoryWatchlistRepo


def vec(seed, dim=128):
    return np.random.default_rng(seed).normal(size=dim).astype(np.float32)


def near(v, noise=0.05, seed=99):
    return l2_normalize(l2_normalize(v) + noise * l2_normalize(vec(seed, len(v))))


# ------------------------------------------------------------------ embeddings
def test_normalize_cosine_and_bytes_round_trip():
    v = vec(1)
    assert abs(np.linalg.norm(l2_normalize(v)) - 1.0) < 1e-6
    assert cosine(v, v * 5) == pytest.approx(1.0, abs=1e-6)
    assert np.allclose(from_bytes(to_bytes(l2_normalize(v)), 128), l2_normalize(v))
    with pytest.raises(ValueError):
        from_bytes(to_bytes(v), 64)


@pytest.mark.parametrize("bad", [np.zeros(128), np.full(128, np.nan), np.ones((2, 64)), np.ones(8)])
def test_invalid_embeddings_are_rejected(bad):
    with pytest.raises(ValueError):
        validate_embedding(bad)


# ------------------------------------------------------------------ aggregation
def test_aggregate_is_a_quality_weighted_normalized_mean():
    a = EmbeddingAggregator()
    a.add(vec(1), 1.0, 0.0)
    a.add(vec(2), 0.01, 0.0)
    agg = a.aggregate()
    assert abs(np.linalg.norm(agg) - 1.0) < 1e-6 and cosine(agg, vec(1)) > 0.99     # dominated by the good one


def test_consistency_is_high_for_one_person_and_low_for_mixed_people():
    same, mixed = EmbeddingAggregator(), EmbeddingAggregator()
    base = vec(1)
    for s in range(5):
        same.add(near(base, 0.1, s), 1.0, 0.0)
    for s in range(6):
        mixed.add(vec(10) if s % 2 == 0 else vec(20), 1.0, 0.0)
    assert same.consistency() > 0.9 and mixed.consistency() < 0.8
    assert EmbeddingAggregator().aggregate() is None


def test_aggregator_drops_the_lowest_quality_item_when_full():
    a = EmbeddingAggregator(max_items=3)
    for i, q in enumerate([0.9, 0.2, 0.8, 0.7]):
        a.add(vec(i), q, 0.0)
    assert len(a) == 3 and min(item[1] for item in a.items) == 0.7


# ------------------------------------------------------------------ decisions
class E:                                       # a stand-in for a watchlist entry
    def __init__(self, i):
        self.watchlist_id = i


CFG = FaceConfig(review_threshold=0.5, alert_threshold=0.7, min_embeddings=3, min_consistency=0.8, min_margin=0.05)


@pytest.mark.parametrize("results, n, cons, kw, status, reason", [
    ([], 5, 0.95, {}, None, "empty_gallery"),
    ([(E(1), 0.9)], 2, 0.95, {}, None, "too_few_embeddings"),
    ([(E(1), 0.9)], 5, 0.60, {}, None, "inconsistent"),
    ([(E(1), 0.40)], 5, 0.95, {}, None, "below_threshold"),
    ([(E(1), 0.80), (E(2), 0.78)], 5, 0.95, {}, None, "ambiguous"),
    ([(E(1), 0.80), (E(2), 0.30)], 5, 0.95, {}, "review", "ok"),                         # allow_alert is False by default
    ([(E(1), 0.80), (E(2), 0.30)], 5, 0.95, {"allow_alert": True}, "alert", "ok"),
    ([(E(1), 0.60), (E(2), 0.30)], 5, 0.95, {"allow_alert": True}, "review", "ok"),      # above review, below alert
    ([(E(1), 0.80)], 5, 0.95, {}, "review", "ok"),                                       # a single entry has no margin issue
])
def test_face_decision_rules(results, n, cons, kw, status, reason):
    cfg = FaceConfig(**{**CFG.__dict__, **kw})
    d = decide_face_match(results, n, cons, cfg)
    assert d.status == status and d.reason == reason


def test_score_mapping_is_anchored_at_the_threshold():
    assert similarity_score(0.5, 0.5) == 50 and similarity_score(1.0, 0.5) == 100
    assert similarity_score(0.0, 0.5) == 0 and 50 < similarity_score(0.7, 0.5) < 100


def test_configuration_defaults_are_safe_and_validated():
    cfg = IdentityConfig.from_config({"face": {"review_threshold": 0.5, "alert_threshold": 0.7}, "typo": 1})
    assert cfg.enabled is False and cfg.save_crops is False and cfg.face.allow_alert is False
    with pytest.raises(ValueError):
        FaceConfig(review_threshold=0.8, alert_threshold=0.5)
    with pytest.raises(ValueError):
        FaceConfig(engine="magic")
    with pytest.raises(ValueError):
        ReidConfig(similarity_threshold=2.0)


# ------------------------------------------------------------------ face gallery
def test_face_gallery_search_ranks_and_filters_by_model():
    repo = InMemoryWatchlistRepo()
    a = repo.add_face("FACE", "subject-001", "A", "LOW", vec(1), "m1")
    repo.add_face("FACE", "subject-002", "B", "LOW", vec(2), "m1")
    repo.add_face("FACE", "subject-003", "C", "LOW", vec(3), "other-model")
    g = FaceGallery(repo, "m1")
    assert g.reload() and len(g) == 2
    top = g.search(near(vec(1)), top_k=2)
    assert top[0][0].watchlist_id == a.watchlist_id and top[0][1] > 0.9 and top[0][1] > top[1][1]


def test_face_gallery_keeps_its_matrix_during_an_outage_and_sees_new_enrollments_after():
    repo = InMemoryWatchlistRepo()
    repo.add_face("FACE", "subject-001", "A", "LOW", vec(1), "m")
    g = FaceGallery(repo, "m")
    g.reload()
    repo.fail = True
    assert g.reload() is False and len(g) == 1                 # old data kept
    repo.fail = False
    repo.add_face("FACE", "subject-002", "B", "LOW", vec(2), "m")
    g.reload()
    assert len(g) == 2


def test_face_gallery_rejects_a_model_mismatch_and_handles_empty():
    repo = InMemoryWatchlistRepo()
    g = FaceGallery(repo, "m")
    g.reload()
    assert g.search(vec(1)) == []
    repo.add_face("FACE", "subject-001", "A", "LOW", vec(1, 128), "m")
    g.reload()
    with pytest.raises(ValueError):
        g.search(vec(1, 64))


# ------------------------------------------------------------------ Re-ID gallery
def item(cam, tid, v, first=0.0, last=10.0):
    return ReidItem(cam, tid, l2_normalize(v), first, last, 5)


def test_reid_gallery_only_compares_across_cameras_within_the_window():
    g = ReidGallery(ttl_s=900, max_gap_s=600)
    g.add(item("A", 1, vec(1), 0, 10))
    g.add(item("B", 2, vec(2), 0, 10))
    hits = g.search(near(vec(1)), camera_id="B", first_seen=60.0)
    assert [(h.camera_id, h.track_id) for h in hits][0] == ("A", 1) and hits[0].gap_s == pytest.approx(50.0)
    assert all(h.camera_id != "B" for h in hits)                       # never the same camera
    assert g.search(near(vec(1)), camera_id="B", first_seen=5000.0) == []     # too long ago


def test_reid_gallery_overlap_and_camera_pairs():
    g = ReidGallery(allow_overlap=False)
    g.add(item("A", 1, vec(1), 0, 100))
    assert g.search(vec(1), "B", first_seen=50.0) == []                 # overlapping in time, not allowed
    g2 = ReidGallery(allow_overlap=True, camera_pairs=[["A", "C"]])
    g2.add(item("A", 1, vec(1), 0, 10))
    assert g2.search(vec(1), "B", 20.0) == []                           # pair A-B is not listed
    assert len(g2.search(vec(1), "C", 20.0)) == 1


def test_reid_gallery_forgets_old_items_and_is_bounded():
    g = ReidGallery(ttl_s=100, max_items=3)
    for i in range(5):
        g.add(item("A", i, vec(i), 0, float(i)))
    assert len(g) == 3
    g.prune(now=500.0)
    assert len(g) == 0


# ------------------------------------------------------------------ metrics
def test_pair_similarities_and_threshold_table():
    people = {"p1": [near(vec(1), 0.05, s) for s in range(3)], "p2": [near(vec(2), 0.05, s) for s in range(3)]}
    genuine, impostor = pair_similarities(people)
    assert len(genuine) == 6 and len(impostor) == 9
    assert min(genuine) > max(impostor)
    rows = threshold_table(genuine, impostor, [0.2, 0.9])
    assert rows[0][1] == 1.0 and rows[1][2] == 0.0
    eer, _ = equal_error_rate(genuine, impostor)
    assert eer == pytest.approx(0.0, abs=1e-9)


def test_threshold_for_far_and_false_match_arithmetic():
    impostor = [0.1] * 90 + [0.5] * 9 + [0.9]
    t = threshold_for_far([0.8] * 10, impostor, 0.01)
    assert t is not None and 0.5 <= t <= 0.9
    assert expected_false_matches(0.001, 50, 1000) == pytest.approx(1000 * (1 - 0.999 ** 50))
    assert expected_false_matches(0.0, 50, 1000) == 0.0


def test_rank_k_accuracy():
    gallery = [("a", l2_normalize(vec(1))), ("b", l2_normalize(vec(2))), ("c", l2_normalize(vec(3)))]
    queries = [("a", near(vec(1))), ("b", near(vec(2))), ("c", near(vec(1)))]      # the third query is wrong
    acc = rank_k_accuracy(queries, gallery, ks=(1, 3))
    assert acc[1] == pytest.approx(2 / 3) and acc[3] == 1.0
