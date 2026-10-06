from app.analytics.rules_config import ZoneRule
from app.analytics.zones import ZoneEngine
from app.schemas.events import LOITERING, ZONE_DWELL, ZONE_ENTER, ZONE_EXIT
from rules_helpers import Harness, obj

SQUARE = [(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)]   # px: x 160-480, y 120-360


def zone(**kw):
    return ZoneRule(id="Z1", name="Restricted", polygon=SQUARE, type="restricted", **kw)


def engine(**zone_kw):
    return ZoneEngine([zone(**zone_kw)], min_track_hits=3)


def test_walk_through_gives_one_enter_and_one_exit():
    h = Harness(engine())
    for i in range(50):
        h.step([obj(1, 100 + 10 * i, 240)])
    assert h.types == [ZONE_ENTER, ZONE_EXIT]
    assert 3.0 < h.events[1].dwell_s < 3.4
    assert h.events[0].details["spawned_inside"] is False


def test_edge_jitter_creates_no_events():
    h = Harness(engine())
    for i in range(40):
        h.step([obj(1, 150 if i % 2 == 0 else 170, 240)])       # flips every frame
    assert h.events == []


def test_dwell_alert_fires_once():
    h = Harness(engine(dwell_alert_s=2.0))
    for _ in range(60):
        h.step([obj(1, 320, 240)])
    assert h.types == [ZONE_ENTER, ZONE_DWELL]


def test_stationary_person_triggers_loitering_once():
    h = Harness(engine(loiter_s=5.0, loiter_max_span=0.05))
    for i in range(120):
        h.step([obj(1, 320 + (i % 3) - 1, 240)])                 # +-1 px jitter
    assert h.types.count(LOITERING) == 1


def test_walking_inside_zone_is_not_loitering():
    h = Harness(engine(loiter_s=5.0, loiter_max_span=0.05))
    for i in range(60):
        h.step([obj(1, 200 + 4 * i, 240)])                       # 240 px over 6 s
    assert LOITERING not in h.types


def test_class_filter():
    h = Harness(engine(classes=["person"]))
    for _ in range(20):
        h.step([obj(1, 320, 240, name="car")])
    assert h.events == []


def test_track_born_inside_is_flagged():
    h = Harness(engine())
    for _ in range(10):
        h.step([obj(1, 320, 240)])
    assert h.events[0].type == ZONE_ENTER
    assert h.events[0].details["spawned_inside"] is True


def test_young_tracks_are_ignored():
    h = Harness(ZoneEngine([zone()], min_track_hits=5))
    for _ in range(4):
        h.step([obj(1, 320, 240)])
    assert h.events == []


def test_removed_track_inside_emits_exit_and_cleans_state():
    eng = engine()
    h = Harness(eng)
    for _ in range(10):
        h.step([obj(1, 320, 240)])
    for _ in range(35):                                          # beyond max_lost_frames=30
        h.step([])
    assert h.types == [ZONE_ENTER, ZONE_EXIT]
    assert h.events[1].details["reason"] == "track_ended"
    assert eng._state == {}
    assert eng.occupancy == {"Z1": 0}


def test_occupancy_counts_confirmed_inside_tracks():
    eng = engine()
    h = Harness(eng)
    for _ in range(6):
        h.step([obj(1, 300, 240), obj(2, 340, 240), obj(3, 50, 50)])
    assert eng.occupancy == {"Z1": 2}
