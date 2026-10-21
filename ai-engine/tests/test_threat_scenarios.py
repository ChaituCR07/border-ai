from threat_helpers import FullScene, watch
from rules_helpers import obj


def walk(scene, name, x, y_from, y_to, step=10, extra_at_start=()):
    sign = 1 if y_to >= y_from else -1
    first = True
    for y in range(y_from, y_to + sign, sign * step):
        scene.step([obj(1, x, y, name)], extra_events=extra_at_start if first else ())
        first = False


def kinds(state):
    return set(state.counted)


def test_plan_scenario_1_restricted_area_at_night_scores_60_high():
    """Person approaches, crosses the virtual line, enters the restricted zone at 02:13 AM."""
    s = FullScene(start="2026-10-12 02:13:00")
    walk(s, "person", 480, 60, 330)
    st = s.state()
    assert kinds(st) == {"line_crossing", "zone_violation", "after_hours"}
    assert (st.score, st.level) == (60, "HIGH")
    assert s.levels == ["LOW", "MEDIUM", "HIGH"]                                   # the score climbs as evidence arrives
    last = s.alerts[-1].details
    assert last["summary"] == "HIGH (60/100): Restricted zone entry +30, Virtual line crossing +20, After-hours movement +10"


def test_the_same_scene_by_day_scores_less():
    s = FullScene(start="2026-10-12 12:13:00")
    walk(s, "person", 480, 60, 330)
    assert (s.state().score, s.state().level) == (50, "MEDIUM")                    # no after-hours evidence


def test_plan_scenario_2_watchlisted_vehicle_scores_100_critical():
    """Watchlisted vehicle enters the restricted zone, crosses the line the wrong way, at night."""
    s = FullScene(start="2026-10-12 02:13:00")
    hit = watch(s.t, entity_type="VEHICLE", status="alert", cls="car", cam="T")
    walk(s, "car", 200, 300, 100, extra_at_start=[hit])                            # cross L1 going OUT (70 HIGH)
    walk(s, "car", 480, 200, 300)                                                  # enter Z1 (+30 -> 100 CRITICAL)
    st = s.state()
    assert kinds(st) == {"watchlist_vehicle", "zone_violation", "direction_violation", "after_hours"}
    assert st.excluded == ["line_crossing"]                                        # the wrong-way crossing counted once
    assert (st.score, st.level) == (100, "CRITICAL")
    assert s.levels[-1] == "CRITICAL" and s.alerts[-1].details["threat_score"] == 100


def test_a_review_grade_watchlist_hit_lowers_scenario_2():
    s = FullScene(start="2026-10-12 02:13:00")
    hit = watch(s.t, entity_type="VEHICLE", status="review", cls="car", cam="T")
    walk(s, "car", 480, 400, 60, extra_at_start=[hit])
    assert s.state().score == 90 and s.state().level == "CRITICAL"                  # 20 + 30 + 20 + 10 (+ bonus 10 = 90)


def test_a_permitted_crossing_outside_the_zone_by_day_stays_low():
    s = FullScene(start="2026-10-12 12:00:00")
    walk(s, "car", 100, 100, 380)                                                  # down = IN = permitted, outside Z1
    st = s.state()
    assert (st.score, st.level) == (20, "LOW") and kinds(st) == {"line_crossing"}


def test_the_plan_section_5_evidence_scores_55_medium():
    """Restricted zone + after hours + loitering over 60 s (no 'unknown person' weight in the table)."""
    s = FullScene(start="2026-10-12 02:13:00")
    for _ in range(75):
        s.step([obj(1, 480, 240, "person")])
    st = s.state()
    assert kinds(st) == {"zone_violation", "after_hours", "loitering"} and (st.score, st.level) == (55, "MEDIUM")


def test_an_alert_carries_what_the_dashboard_needs():
    s = FullScene(start="2026-10-12 02:13:00")
    walk(s, "car", 200, 300, 100, extra_at_start=[watch(s.t, cls="car", cam="T")])
    walk(s, "car", 480, 200, 300)
    alert = s.alerts[-1]
    d = alert.to_dict()
    assert d["severity"] == "CRITICAL" and d["threat_score"] == 100 and d["camera_id"] == "T"
    labels = [c["label"] for c in d["details"]["contributions"]]
    assert "Restricted zone entry" in labels and "Watchlisted vehicle" in labels
