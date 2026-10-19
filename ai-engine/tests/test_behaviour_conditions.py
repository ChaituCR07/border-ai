from app.behaviour.authorized import AuthorizedPlates
from app.behaviour.conditions import Env, evaluate, evaluate_all
from app.behaviour.context import TrackContext
from app.behaviour.rules_config import validate_condition
from behaviour_helpers import IST, epoch, obs

NOW = epoch("2026-10-12 02:13:00")


def cond(**kw):
    return validate_condition(kw, "test")


def ctx(cls="person"):
    c = TrackContext("CAM", 1)
    c.touch(cls, NOW - 100)
    return c


def env(now=NOW, age=20.0, authorized=None):
    return Env(now, IST, age, authorized)


def test_object():
    assert evaluate(cond(type="object", value=["person", "car"]), ctx("car"), env()).ok
    assert not evaluate(cond(type="object", value="person"), ctx("car"), env()).ok


def test_zone_by_type_id_dwell_and_negation():
    c = ctx()
    c.ingest(obs("ZONE_ENTER", NOW - 70, rule_id="Z1", rule_type="restricted"))
    r = evaluate(cond(type="zone", zone_type="restricted"), c, env())
    assert r.ok and r.bindings == {"zone_id": "Z1"} and "70 s" in r.reasons[0]
    assert evaluate(cond(type="zone", zone_id="Z1", min_dwell_s=60), c, env()).ok
    assert not evaluate(cond(type="zone", zone_id="Z1", min_dwell_s=80), c, env()).ok
    assert not evaluate(cond(type="zone", zone_id="Z2"), c, env()).ok
    assert not evaluate(cond(type="zone", zone_type="monitored"), c, env()).ok
    assert evaluate(cond(type="zone", zone_type="any"), c, env()).ok
    assert evaluate(cond(type="zone", zone_type="monitored", inside=False), c, env()).ok
    assert not evaluate(cond(type="zone", zone_type="restricted", inside=False), c, env()).ok
    c.ingest(obs("ZONE_EXIT", NOW - 5, rule_id="Z1"))
    assert not evaluate(cond(type="zone", zone_type="restricted"), c, env()).ok          # left the zone


def test_the_longest_dwell_wins_when_inside_several_zones():
    c = ctx()
    c.ingest(obs("ZONE_ENTER", NOW - 10, rule_id="Z1", rule_type="restricted"))
    c.ingest(obs("ZONE_ENTER", NOW - 90, rule_id="Z2", rule_type="monitored"))
    assert evaluate(cond(type="zone", zone_type="any"), c, env()).bindings == {"zone_id": "Z2"}


def test_line_crossing_direction_expected_direction_window_and_line():
    c = ctx()
    c.ingest(obs("LINE_CROSSING", NOW - 2, rule_id="L1", rule_type="tripwire", rule_kind="line", direction="OUT"))
    assert evaluate(cond(type="line_crossing", line="L1", expected_direction="IN"), c, env()).ok     # OUT != IN
    assert not evaluate(cond(type="line_crossing", line="L1", expected_direction="OUT"), c, env()).ok
    assert evaluate(cond(type="line_crossing", direction="OUT"), c, env()).ok
    assert not evaluate(cond(type="line_crossing", direction="IN"), c, env()).ok
    assert not evaluate(cond(type="line_crossing", line="L2"), c, env()).ok                          # another line
    assert not evaluate(cond(type="line_crossing", line="L1", within_s=1), c, env()).ok              # too long ago
    r = evaluate(cond(type="line_crossing", line="L1", expected_direction="IN"), c, env())
    assert r.bindings["line_id"] == "L1" and "going OUT (expected IN)" in r.reasons[0]


def test_generic_event_condition():
    c = ctx()
    c.ingest(obs("REID_MATCH", NOW - 3, rule_id="REID", rule_kind="identity", rule_type="reid"))
    assert evaluate(cond(type="event", event="reid_match", where={"rule_id": "REID"}, within_s=10), c, env()).ok
    assert not evaluate(cond(type="event", event="REID_MATCH", where={"rule_id": "OTHER"}), c, env()).ok


def test_time_windows_zones_and_days():
    night = cond(type="time", between=["22:00", "05:00"])
    r = evaluate(night, ctx(), env())
    assert r.ok and "02:13" in r.reasons[0]
    assert not evaluate(night, ctx(), env(now=epoch("2026-10-12 12:00:00"))).ok
    assert not evaluate(cond(type="time", between=["22:00", "05:00"], timezone="UTC"), ctx(), env()).ok   # 20:43 UTC
    assert evaluate(cond(type="time", between=["02:00", "03:00"], days=["MON"]), ctx(), env()).ok
    assert not evaluate(cond(type="time", between=["02:00", "03:00"], days=["TUE"]), ctx(), env()).ok


def test_watchlist_condition_filters():
    c = ctx("car")
    assert not evaluate(cond(type="watchlist"), c, env()).ok
    assert evaluate(cond(type="watchlist", present=False), c, env()).ok
    c.ingest(obs("WATCHLIST_MATCH", NOW - 1, rule_id="WATCHLIST", rule_kind="watchlist",
                 details={"status": "review", "risk_level": "HIGH", "entity_type": "VEHICLE"}))
    assert evaluate(cond(type="watchlist"), c, env()).ok
    assert evaluate(cond(type="watchlist", status=["review"], risk_level_min="HIGH"), c, env()).ok
    assert not evaluate(cond(type="watchlist", status=["alert"]), c, env()).ok
    assert not evaluate(cond(type="watchlist", risk_level_min="CRITICAL"), c, env()).ok
    assert not evaluate(cond(type="watchlist", entity_types=["PLATE"]), c, env()).ok
    c.ingest(obs("WATCHLIST_MATCH", NOW, rule_id="WATCHLIST", rule_kind="watchlist",
                 details={"status": "alert", "risk_level": "CRITICAL", "entity_type": "VEHICLE"}))
    assert evaluate(cond(type="watchlist", status=["alert"], risk_level_min="CRITICAL"), c, env()).ok      # the strongest hit is kept


def test_plate_conditions_and_the_unread_plate_case():
    auth = AuthorizedPlates(["TN09AB4567"])
    c = ctx("car")
    for node in (cond(type="plate", authorized=False), cond(type="plate", authorized=True)):
        assert not evaluate(node, c, env(authorized=auth)).ok          # unread: cannot be judged either way
    assert evaluate(cond(type="plate", read=False), c, env()).ok
    c.ingest(obs("PLATE_RECOGNIZED", NOW - 1, rule_id="ANPR", rule_kind="anpr", cls="car",
                 details={"plate": "KA01AB1234", "final": False}))
    assert evaluate(cond(type="plate", read=True), c, env()).ok
    assert evaluate(cond(type="plate", authorized=False), c, env(authorized=auth)).ok
    assert not evaluate(cond(type="plate", authorized=True), c, env(authorized=auth)).ok
    c.ingest(obs("PLATE_RECOGNIZED", NOW, rule_id="ANPR", rule_kind="anpr", cls="car", details={"plate": "TN09AB4567"}))
    assert evaluate(cond(type="plate", authorized=True), c, env(authorized=auth)).ok


def test_track_age():
    assert evaluate(cond(type="track_age", min_s=10), ctx(), env(age=12)).ok
    assert not evaluate(cond(type="track_age", min_s=10), ctx(), env(age=3)).ok


def test_combinators():
    c = ctx()
    c.ingest(obs("ZONE_ENTER", NOW - 5, rule_id="Z1"))
    inside = cond(type="zone", zone_id="Z1")
    old = cond(type="track_age", min_s=999)
    assert evaluate(cond(type="any", conditions=[old, inside]), c, env()).ok
    assert not evaluate(cond(type="all", conditions=[old, inside]), c, env()).ok
    assert evaluate(cond(type="not", condition=old), c, env()).ok
    assert not evaluate(cond(type="not", condition=inside), c, env()).ok
    r = evaluate_all([cond(type="object", value="person"), inside, cond(type="time", between=["22:00", "05:00"])], c, env())
    assert r.ok and len(r.reasons) == 3 and r.bindings == {"zone_id": "Z1"}


def test_the_context_ignores_behaviour_events():
    c = ctx()
    c.ingest(obs("ZONE_VIOLATION", NOW, rule_id="R001", rule_kind="behaviour"))
    assert len(c.events) == 0 and not c.zones
