from app.schemas.tracking import TrackedObject
from app.tracking.track_store import ACTIVE, LOST, TrackStore


def obj(tid, x=100.0, y=200.0, name="person", conf=0.9):
    return TrackedObject(tid, 0, name, conf, x - 10, y - 40, x + 10, y)


def test_new_track_is_active_and_reported():
    s = TrackStore("A", max_lost_frames=3)
    upd = s.update([obj(1)], 0.0)
    assert [t.track_id for t in upd.new] == [1]
    assert s.get(1).state == ACTIVE


def test_lost_then_removed_after_buffer():
    s = TrackStore("A", max_lost_frames=3)
    s.update([obj(1)], 0.0)                       # tick 1
    upd = s.update([], 0.1)                       # tick 2: missed 1
    assert [t.track_id for t in upd.lost] == [1] and s.get(1).state == LOST
    s.update([], 0.2)                             # tick 3: missed 2
    s.update([], 0.3)                             # tick 4: missed 3, still kept
    assert s.get(1) is not None
    upd = s.update([], 0.4)                       # tick 5: missed 4 > 3
    assert [t.track_id for t in upd.removed] == [1]
    assert s.get(1) is None
    assert [t.track_id for t in s.all_tracks()] == [1]      # archived, not lost


def test_reactivation_within_buffer():
    s = TrackStore("A", max_lost_frames=5)
    s.update([obj(1)], 0.0)
    s.update([], 0.1)
    upd = s.update([obj(1)], 0.2)
    assert [t.track_id for t in upd.reactivated] == [1]
    assert s.get(1).state == ACTIVE


def test_majority_class_vote_is_confidence_weighted():
    s = TrackStore("A", max_lost_frames=5)
    s.update([obj(1, name="car", conf=0.9)], 0.0)
    s.update([obj(1, name="car", conf=0.9)], 0.1)
    o = obj(1, name="truck", conf=0.5)
    s.update([o], 0.2)
    assert s.get(1).dominant_class == "car"
    assert o.stable_class == "car"


def test_trail_is_bounded_and_uses_ground_point():
    s = TrackStore("A", max_lost_frames=5, trail_length=5)
    for i in range(12):
        s.update([obj(1, x=100 + i)], i * 0.1)
    t = s.get(1)
    assert len(t.trail) == 5
    assert t.last_point == (111.0, 200.0)       # bottom-center of the last box


def test_age_and_duration():
    s = TrackStore("A", max_lost_frames=5)
    s.update([obj(1)], 10.0)
    o = obj(1)
    s.update([o], 12.5)
    assert abs(o.age_s - 2.5) < 1e-6
