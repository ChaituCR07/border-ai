from app.analytics.lines import LineEngine
from app.analytics.rules_config import LineRule
from app.schemas.events import LINE_CROSSING
from rules_helpers import Harness, obj


def line(**kw):
    base = dict(id="L1", name="Entry", p1=(0.0, 0.5), p2=(1.0, 0.5))     # y = 240 px
    base.update(kw)
    return LineRule(**base)


def engine(**kw):
    return LineEngine([line(**kw)], min_track_hits=3)


def test_top_to_bottom_is_positive_direction():
    h = Harness(engine())
    for y in range(100, 390, 10):
        h.step([obj(1, 320, y)])
    assert [e.type for e in h.events] == [LINE_CROSSING]
    assert h.events[0].direction == "IN"


def test_bottom_to_top_is_opposite_direction():
    h = Harness(engine())
    for y in range(380, 90, -10):
        h.step([obj(1, 320, y)])
    assert [e.direction for e in h.events] == ["OUT"]


def test_positive_direction_label_can_be_flipped():
    h = Harness(engine(positive_direction="OUT"))
    for y in range(100, 390, 10):
        h.step([obj(1, 320, y)])
    assert h.events[0].direction == "OUT"


def test_hovering_inside_the_band_creates_no_events():
    h = Harness(engine())                                  # band = 0.01 * 640 = 6.4 px
    for i in range(60):
        h.step([obj(1, 320, 236 if i % 2 == 0 else 244)])
    assert h.events == []


def test_rapid_oscillation_across_the_band_is_limited_by_cooldown():
    h = Harness(engine(cooldown_s=2.0))
    for i in range(20):                                    # 2 s of flipping 200 <-> 280
        h.step([obj(1, 320, 200 if i % 2 == 0 else 280)])
    assert len(h.events) == 1


def test_walking_around_the_end_of_a_short_line_is_ignored():
    h = Harness(engine(p1=(0.3, 0.5), p2=(0.7, 0.5)))       # line spans x 192-448
    for y in range(100, 390, 10):
        h.step([obj(1, 576, y)])                           # crosses the extension, not the segment
    assert h.events == []


def test_class_filter():
    h = Harness(engine(classes=["person"]))
    for y in range(100, 390, 10):
        h.step([obj(1, 320, y, name="car")])
    assert h.events == []


def test_young_tracks_are_ignored():
    h = Harness(LineEngine([line()], min_track_hits=50))
    for y in range(100, 390, 10):
        h.step([obj(1, 320, y)])
    assert h.events == []


def test_counts_and_state_cleanup_on_removal():
    eng = engine()
    h = Harness(eng)
    for y in range(100, 390, 10):
        h.step([obj(1, 320, y)])
    for _ in range(35):
        h.step([])
    assert eng.counts["L1"] == {"IN": 1, "OUT": 0}
    assert eng._state == {}


def test_two_tracks_cross_independently():
    h = Harness(engine())
    for k in range(29):
        h.step([obj(1, 200, 100 + 10 * k), obj(2, 440, 380 - 10 * k)])
    assert sorted(e.direction for e in h.events) == ["IN", "OUT"]
