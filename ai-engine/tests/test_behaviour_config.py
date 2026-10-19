import json

import pytest

from app import config as app_config
from app.behaviour.authorized import AuthorizedPlates
from app.behaviour.rules_config import (check_rules_against_zones, load_behaviour_config,
                                        parse_behaviour_config, walk_conditions)
from app.behaviour.timeutil import (get_zone, in_window, local_minutes_and_day, parse_clock_start,
                                    parse_hhmm)
from behaviour_helpers import IST, epoch, make_cfg, make_rule


def cfg_with(*rules, **top):
    return {"version": 1, "site": {"timezone": "Asia/Kolkata"}, "rules": list(rules), **top}


# ------------------------------------------------------------------ valid files and defaults
def test_defaults_are_filled_in():
    cfg = make_cfg([make_rule(conditions=[{"type": "zone", "zone_type": "restricted"},
                                          {"type": "line_crossing", "expected_direction": "in"},
                                          {"type": "object", "value": "person"}])])
    r = cfg.rules[0]
    zone, line, obj_ = r.conditions
    assert zone["inside"] is True and zone["min_dwell_s"] == 0.0
    assert line["within_s"] == 5.0 and line["expected_direction"] == "IN"
    assert obj_["value"] == ["person"]
    assert (r.enabled, r.cooldown_s, r.rearm_s, r.points, r.severity) == (True, 0.0, 30.0, 30, "HIGH")


def test_nested_conditions_are_validated_and_walkable():
    cond = {"type": "any", "conditions": [{"type": "not", "condition": {"type": "zone", "zone_id": "Z1"}},
                                          {"type": "track_age", "min_s": 5}]}
    cfg = make_cfg([make_rule(conditions=[cond])])
    assert [c["type"] for c in walk_conditions(cfg.rules[0].conditions)] == ["any", "not", "zone", "track_age"]


# ------------------------------------------------------------------ every kind of mistake is rejected
GOOD = make_rule()


@pytest.mark.parametrize("mutate, message", [
    (lambda r: r.update(rule_id=""), "rule_id"),
    (lambda r: r.update(name=""), "name"),
    (lambda r: r.update(event_type="zone violation"), "event_type"),
    (lambda r: r.update(event_type="ZONE_ENTER"), "observation name"),
    (lambda r: r.update(event_type="LOITERING"), "observation name"),
    (lambda r: r.update(action={"severity": "SEVERE", "score": 10}), "severity"),
    (lambda r: r.update(action={"severity": "HIGH", "score": 101}), "score"),
    (lambda r: r.update(action={"severity": "HIGH", "score": 12.5}), "whole number"),
    (lambda r: r.update(action={"severity": "HIGH"}), "score"),
    (lambda r: r.update(conditions=[]), "conditions"),
    (lambda r: r.update(conditions=[{"type": "teleport"}]), "unknown condition type"),
    (lambda r: r.update(conditions=[{"type": "object", "value": "person", "colour": "red"}]), "unknown keys"),
    (lambda r: r.update(conditions=[{"type": "object", "value": []}]), "value"),
    (lambda r: r.update(conditions=[{"type": "zone"}]), "zone_id"),
    (lambda r: r.update(conditions=[{"type": "zone", "zone_id": "Z1", "min_dwell_s": -1}]), "min_dwell_s"),
    (lambda r: r.update(conditions=[{"type": "line_crossing", "direction": "IN", "expected_direction": "OUT"}]), "not both"),
    (lambda r: r.update(conditions=[{"type": "line_crossing", "direction": "SIDEWAYS"}]), "direction"),
    (lambda r: r.update(conditions=[{"type": "time", "between": ["25:00", "05:00"]}]), "out of range"),
    (lambda r: r.update(conditions=[{"type": "time", "between": ["10:00", "10:00"]}]), "differ"),
    (lambda r: r.update(conditions=[{"type": "time", "between": "22:00-05:00"}]), "between"),
    (lambda r: r.update(conditions=[{"type": "time", "between": ["22:00", "05:00"], "timezone": "Mars/Olympus"}]), "time zone"),
    (lambda r: r.update(conditions=[{"type": "time", "between": ["22:00", "05:00"], "days": ["FUNDAY"]}]), "days"),
    (lambda r: r.update(conditions=[{"type": "watchlist", "risk_level_min": "EXTREME"}]), "risk_level_min"),
    (lambda r: r.update(conditions=[{"type": "plate"}]), "read"),
    (lambda r: r.update(conditions=[{"type": "all", "conditions": []}]), "non-empty"),
    (lambda r: r.update(conditions=[{"type": "track_age"}]), "min_s"),
    (lambda r: r.update(cooldown_s=-5), "cooldown_s"),
    (lambda r: r.update(enabled="yes"), "enabled"),
])
def test_invalid_rules_are_rejected_with_a_clear_message(mutate, message):
    rule = json.loads(json.dumps(GOOD))
    mutate(rule)
    with pytest.raises(ValueError, match=message):
        parse_behaviour_config(cfg_with(rule))


def test_duplicate_rule_ids_and_bad_file_level_values_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        parse_behaviour_config(cfg_with(make_rule("R1"), make_rule("R1")))
    with pytest.raises(ValueError, match="version"):
        parse_behaviour_config({"version": 2, "rules": []})
    with pytest.raises(ValueError, match="time zone"):
        parse_behaviour_config({"version": 1, "site": {"timezone": "Nowhere/Land"}, "rules": []})
    with pytest.raises(ValueError, match="rules"):
        parse_behaviour_config({"version": 1, "rules": "nope"})


def test_authorization_rules_need_an_authorized_list():
    rule = make_rule(conditions=[{"type": "plate", "authorized": False}])
    with pytest.raises(ValueError, match="authorized_plates_csv"):
        parse_behaviour_config(cfg_with(rule))
    parse_behaviour_config(cfg_with(rule, authorized_plates_csv="configs/authorized.csv"))   # accepted
    disabled = make_rule(conditions=[{"type": "plate", "authorized": False}], enabled=False)
    parse_behaviour_config(cfg_with(disabled))                   # a disabled rule does not matter


def test_per_camera_time_zones():
    cfg = parse_behaviour_config({"version": 1, "site": {"timezone": "UTC", "cameras": {"CAM_9": {"timezone": "Asia/Kolkata"}}},
                                  "rules": []})
    assert cfg.camera_timezones == {"CAM_9": "Asia/Kolkata"}


# ------------------------------------------------------------------ cross-check with the zone files
def write_zones(tmp_path, camera, zone_id="Z1", zone_type="restricted", line_id="L1"):
    (tmp_path / f"{camera}.json").write_text(json.dumps({
        "camera_id": camera,
        "zones": [{"id": zone_id, "name": "n", "type": zone_type, "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]]}],
        "lines": [{"id": line_id, "name": "l", "p1": [0, 0.5], "p2": [1, 0.5]}]}))


def test_zone_cross_check_catches_typos(tmp_path):
    write_zones(tmp_path, "CAM_1")
    ok = make_cfg([make_rule(conditions=[{"type": "zone", "zone_type": "restricted"},
                                         {"type": "line_crossing", "line": "L1"}])])
    assert check_rules_against_zones(ok, tmp_path) == ([], [])
    typo = make_cfg([make_rule(conditions=[{"type": "zone", "zone_id": "ZZ"}])])
    errors, _ = check_rules_against_zones(typo, tmp_path)
    assert errors and "ZZ" in errors[0]
    wrong_line = make_cfg([make_rule(conditions=[{"type": "line_crossing", "line": "L9"}])])
    assert check_rules_against_zones(wrong_line, tmp_path)[0]


def test_cross_check_with_named_cameras_and_partial_coverage(tmp_path):
    write_zones(tmp_path, "CAM_1")
    write_zones(tmp_path, "CAM_2", zone_id="Z9", zone_type="monitored")
    rule_all = make_cfg([make_rule(conditions=[{"type": "zone", "zone_id": "Z1"}])])
    errors, warnings = check_rules_against_zones(rule_all, tmp_path)
    assert errors == [] and warnings                              # defined on one camera: only a warning
    rule_named = make_cfg([make_rule(conditions=[{"type": "zone", "zone_id": "Z1"}], cameras=["CAM_1", "CAM_2"])])
    assert check_rules_against_zones(rule_named, tmp_path)[0]      # missing on CAM_2: an error
    unknown_cam = make_cfg([make_rule(conditions=[{"type": "zone", "zone_id": "Z1"}], cameras=["CAM_7"])])
    assert check_rules_against_zones(unknown_cam, tmp_path)[0]


# ------------------------------------------------------------------ time helpers
def test_time_windows():
    night = (parse_hhmm("22:00"), parse_hhmm("05:00"))
    assert in_window(parse_hhmm("23:30"), *night) and in_window(parse_hhmm("02:13"), *night)
    assert in_window(parse_hhmm("22:00"), *night) and not in_window(parse_hhmm("05:00"), *night)   # start in, end out
    assert not in_window(parse_hhmm("12:00"), *night)
    day = (parse_hhmm("09:00"), parse_hhmm("17:00"))
    assert in_window(parse_hhmm("09:00"), *day) and not in_window(parse_hhmm("17:00"), *day)


def test_the_same_instant_is_a_different_local_time_in_another_zone():
    t = epoch("2026-10-12 02:13:00", IST)
    assert local_minutes_and_day(t, IST) == (2 * 60 + 13, "MON")
    assert local_minutes_and_day(t, get_zone("UTC")) == (20 * 60 + 43, "SUN")


def test_clock_start_parsing():
    assert parse_clock_start("2026-10-12T02:13:00", IST) == epoch("2026-10-12 02:13:00", IST)
    assert parse_clock_start("2026-10-12T02:13:00+00:00", IST) != epoch("2026-10-12 02:13:00", IST)
    with pytest.raises(ValueError):
        parse_hhmm("noon")


# ------------------------------------------------------------------ authorized plates
def test_authorized_plates_are_normalized_and_loaded_from_csv(tmp_path):
    f = tmp_path / "ok.csv"
    f.write_text("plate,label\nka-05 mn 2468,Demo one\nTN09AB4567,Demo two\n")
    auth = AuthorizedPlates.from_csv(f)
    assert len(auth) == 2 and auth.contains("KA05MN2468") and auth.contains("tn 09 ab 4567")
    assert not auth.contains("KA01AB1234")


def test_a_missing_authorized_list_is_empty_not_a_crash(tmp_path):
    assert len(AuthorizedPlates.from_csv(tmp_path / "missing.csv")) == 0


# ------------------------------------------------------------------ the shipped default rule pack
def test_the_default_rule_pack_is_valid_and_contains_the_plan_rules():
    path = app_config.CONFIG_DIR / "rules.json"
    if not path.exists():
        pytest.skip("configs/rules.json not created yet")
    cfg = load_behaviour_config(path)
    types = {r.event_type for r in cfg.rules}
    assert {"ZONE_VIOLATION", "DIRECTION_VIOLATION", "LOITERING_VIOLATION", "AFTER_HOURS_ACTIVITY"} <= types
    assert {r.rule_id: r.points for r in cfg.rules if r.rule_id in ("R001", "R002", "R003", "R004")} == \
        {"R001": 30, "R002": 20, "R003": 15, "R004": 10}                  # the weights from the plan's table
