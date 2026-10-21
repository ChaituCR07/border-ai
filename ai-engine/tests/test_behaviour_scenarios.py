from app.behaviour.authorized import AuthorizedPlates
from behaviour_helpers import GeometryScene, make_rule, obs
from rules_helpers import obj

ALL = ["person", "car", "truck", "bus", "motorcycle", "bicycle"]
R001 = make_rule("R001", [{"type": "object", "value": ALL}, {"type": "zone", "zone_type": "restricted"}],
                 "ZONE_VIOLATION", "HIGH", 30)
R002 = make_rule("R002", [{"type": "object", "value": ALL},
                          {"type": "line_crossing", "line": "L1", "expected_direction": "IN"}],
                 "DIRECTION_VIOLATION", "MEDIUM", 20)
R003 = make_rule("R003", [{"type": "object", "value": ["person"]},
                          {"type": "zone", "zone_type": "any", "min_dwell_s": 60}],
                 "LOITERING_VIOLATION", "MEDIUM", 15)
R004 = make_rule("R004", [{"type": "object", "value": ALL}, {"type": "time", "between": ["22:00", "05:00"]},
                          {"type": "track_age", "min_s": 2}],
                 "AFTER_HOURS_ACTIVITY", "LOW", 10, rearm_s=3600)
R005 = make_rule("R005", [{"type": "object", "value": ["car", "truck", "bus", "motorcycle"]},
                          {"type": "zone", "zone_type": "restricted"},
                          {"type": "time", "between": ["22:00", "05:00"]},
                          {"type": "plate", "authorized": False}],
                 "UNAUTHORIZED_VEHICLE_AFTER_HOURS", "CRITICAL", 40)
RULES = [R001, R002, R003, R004, R005]


def walk(scene, name, x, y_from, y_to, step=10):
    """Move an object straight down (or up) the frame at column x."""
    sign = 1 if y_to >= y_from else -1
    for y in range(y_from, y_to + sign, sign * step):
        scene.step([obj(1, x, y, name)])


# ------------------------------------------------------------------ plan Test 1 / Test 2
def test_plan_test_1_person_outside_the_restricted_zone_gives_no_alert():
    s = GeometryScene(RULES)
    walk(s, "person", 100, 60, 400)                      # far left of zone Z1 (x 352-608)
    assert [e for e in s.results if e.type == "ZONE_VIOLATION"] == []
    assert s.results == []                               # nothing at all: daytime, permitted direction


def test_plan_test_2_person_entering_the_restricted_zone_gives_a_zone_alert():
    s = GeometryScene(RULES)
    walk(s, "person", 480, 60, 300)                      # straight into Z1
    alerts = [e for e in s.results if e.type == "ZONE_VIOLATION"]
    assert len(alerts) == 1
    assert alerts[0].details["severity"] == "HIGH" and alerts[0].details["points"] == 30
    assert alerts[0].details["bindings"] == {"zone_id": "Z1"}


# ------------------------------------------------------------------ plan Test 5 / Test 6
def test_plan_test_5_vehicle_crossing_in_the_permitted_direction_gives_no_violation():
    s = GeometryScene(RULES)
    walk(s, "car", 100, 100, 380)                        # top to bottom = IN (expected)
    assert any(e.type == "LINE_CROSSING" and e.direction == "IN" for e in s.observations)
    assert [e for e in s.results if e.type == "DIRECTION_VIOLATION"] == []


def test_plan_test_6_vehicle_crossing_the_wrong_way_gives_a_direction_violation():
    s = GeometryScene(RULES)
    walk(s, "car", 100, 380, 100)                        # bottom to top = OUT (expected IN)
    violations = [e for e in s.results if e.type == "DIRECTION_VIOLATION"]
    assert len(violations) == 1 and violations[0].details["points"] == 20
    assert "going OUT (expected IN)" in violations[0].details["reasons"][-1]


# ------------------------------------------------------------------ plan behaviours
def test_loitering_needs_more_than_sixty_seconds_in_a_zone():
    s = GeometryScene(RULES)
    for _ in range(50):
        s.step([obj(1, 480, 240)])                       # 50 s in Z1
    assert "LOITERING_VIOLATION" not in s.types
    for _ in range(25):
        s.step([obj(1, 480, 240)])                       # 75 s
    assert s.types.count("LOITERING_VIOLATION") == 1
    for _ in range(40):
        s.step([obj(1, 480, 240)])
    assert s.types.count("LOITERING_VIOLATION") == 1     # reported once


def test_leaving_before_sixty_seconds_is_not_loitering():
    s = GeometryScene(RULES)
    for _ in range(40):
        s.step([obj(1, 480, 240)])                       # 40 s inside Z1
    for _ in range(15):
        s.step([obj(1, 100, 240)])                       # walked out
    assert "LOITERING_VIOLATION" not in s.types


def test_after_hours_depends_on_the_local_clock():
    night = GeometryScene(RULES, start="2026-10-12 02:13:00")
    day = GeometryScene(RULES, start="2026-10-12 12:13:00")
    for s in (night, day):
        for _ in range(8):
            s.step([obj(1, 100, 240, "person")])
    assert night.types.count("AFTER_HOURS_ACTIVITY") == 1
    assert "AFTER_HOURS_ACTIVITY" not in day.types
    assert night.results[0].details["reasons"][1].startswith("local time 02:13")


def test_the_after_hours_rule_follows_the_configured_time_zone():
    utc = GeometryScene(RULES, start="2026-10-12 02:13:00", tz="UTC")          # 02:13 UTC: also night
    ist_as_utc = GeometryScene(RULES, start="2026-10-12 02:13:00", tz="Asia/Kolkata")
    assert utc.behaviour._tz("T").key == "UTC" and ist_as_utc.behaviour._tz("T").key == "Asia/Kolkata"


# ------------------------------------------------------------------ plan Scenario 1
def test_plan_scenario_1_restricted_area_at_night():
    """Person approaches, crosses the virtual line, enters the restricted zone, at 02:13 AM."""
    s = GeometryScene(RULES, start="2026-10-12 02:13:00")
    walk(s, "person", 480, 60, 330)
    assert any(e.type == "LINE_CROSSING" for e in s.observations)               # observation: line crossing
    types = [e.type for e in s.results]
    assert sorted(types) == ["AFTER_HOURS_ACTIVITY", "ZONE_VIOLATION"]
    assert sum(e.details["points"] for e in s.results) == 40                    # +20 for the crossing makes the plan's 60
    assert all("reasons" in e.details and e.details["reasons"] for e in s.results)


# ------------------------------------------------------------------ plan Section 38 example and Scenario 2 inputs
def test_section_38_unauthorized_vehicle_at_night_in_a_restricted_zone():
    auth = AuthorizedPlates(["TN09AB4567"])
    s = GeometryScene(RULES, start="2026-10-12 23:30:00", authorized=auth, authorized_plates_csv="configs/x.csv")
    plate = obs("PLATE_RECOGNIZED", s.t, cls="car", rule_id="ANPR", rule_kind="anpr", rule_type="plate",
                details={"plate": "KA01AB1234", "final": False})
    for _ in range(4):
        s.step([obj(1, 480, 240, "car")])
    assert "UNAUTHORIZED_VEHICLE_AFTER_HOURS" not in s.types            # plate not read yet: cannot judge
    s.step([obj(1, 480, 240, "car")], extra_events=[plate])             # the plate arrives (from the ANPR thread)
    critical = [e for e in s.results if e.type == "UNAUTHORIZED_VEHICLE_AFTER_HOURS"]
    assert len(critical) == 1 and critical[0].details["severity"] == "CRITICAL"
    assert critical[0].details["plate"] == "KA01AB1234"


def test_an_authorized_plate_does_not_trigger_the_section_38_rule():
    auth = AuthorizedPlates(["TN09AB4567"])
    s = GeometryScene(RULES, start="2026-10-12 23:30:00", authorized=auth, authorized_plates_csv="configs/x.csv")
    plate = obs("PLATE_RECOGNIZED", s.t, cls="car", rule_id="ANPR", rule_kind="anpr", rule_type="plate",
                details={"plate": "TN09AB4567", "final": True})
    for _ in range(5):
        s.step([obj(1, 480, 240, "car")], extra_events=[plate] if _ == 0 else [])
    assert "UNAUTHORIZED_VEHICLE_AFTER_HOURS" not in s.types
    assert "ZONE_VIOLATION" in s.types                                  # the restricted-zone rule still applies


def test_watchlist_observations_are_available_to_rules():
    watch_rule = make_rule("RW", [{"type": "watchlist", "risk_level_min": "HIGH"},
                                  {"type": "zone", "zone_type": "restricted"}],
                           "WATCHLISTED_IN_RESTRICTED_ZONE", "CRITICAL", 40)
    s = GeometryScene([watch_rule])
    hit = obs("WATCHLIST_MATCH", s.t, cls="car", rule_id="WATCHLIST", rule_kind="watchlist",
              details={"status": "alert", "risk_level": "HIGH", "entity_type": "VEHICLE"})
    s.step([obj(1, 480, 240, "car")], extra_events=[hit])
    for _ in range(5):
        s.step([obj(1, 480, 240, "car")])
    assert s.types == ["WATCHLISTED_IN_RESTRICTED_ZONE"]
    assert s.results[0].details["watchlist"] == {"status": "alert", "risk_level": "HIGH"}


def test_two_objects_are_judged_independently():
    s = GeometryScene(RULES)
    for y in range(60, 300, 10):
        s.step([obj(1, 480, y, "person"), obj(2, 100, y, "person")])        # one enters the zone, one does not
    violating = {e.track_id for e in s.results if e.type == "ZONE_VIOLATION"}
    assert violating == {1}
