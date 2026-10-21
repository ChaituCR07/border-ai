import copy
import json

import pytest

from app import config as app_config
from app.behaviour.rules_config import parse_behaviour_config
from app.threat.config import (check_scoring_against_rules, load_scoring_config, parse_scoring_config,
                               source_matches)
from behaviour_helpers import make_cfg, make_rule, obs
from threat_helpers import DEFAULT_SCORING, make_scoring


def cfg_data(mutate):
    data = copy.deepcopy(DEFAULT_SCORING)
    mutate(data)
    return {"scoring": data}


def test_default_levels_follow_the_plan_bands():
    cfg = make_scoring()
    for score, level in [(0, "LOW"), (29, "LOW"), (30, "MEDIUM"), (59, "MEDIUM"),
                         (60, "HIGH"), (79, "HIGH"), (80, "CRITICAL"), (100, "CRITICAL")]:
        assert cfg.level_for(score) == level


def test_levels_are_configurable():
    levels = [{"name": "LOW", "min": 0}, {"name": "MEDIUM", "min": 20},
              {"name": "HIGH", "min": 50}, {"name": "CRITICAL", "min": 90}]
    cfg = make_scoring(levels=levels)
    assert cfg.level_for(55) == "HIGH" and cfg.level_for(85) == "HIGH" and cfg.level_for(90) == "CRITICAL"


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d.pop("levels"), "levels"),
    (lambda d: d["levels"].pop(), "levels"),
    (lambda d: d["levels"][0].update(min=5), "start at 0"),
    (lambda d: d["levels"][2].update(min=20), "increase"),
    (lambda d: d["levels"][3].update(min=500), "exceeds max_score"),
    (lambda d: d.update(window_s=0), "window_s"),
    (lambda d: d.update(alert_min_score=500), "alert_min_score"),
    (lambda d: d.update(merge_scope="planet"), "merge_scope"),
    (lambda d: d.update(typo_key=1), "unknown scoring keys"),
    (lambda d: d.update(sources=[]), "sources"),
    (lambda d: d["sources"][0].update(id="Zone Violation"), "'id'"),
    (lambda d: d["sources"][0].update(id="multiple_suspicious"), "'id'"),
    (lambda d: d["sources"][1].update(id="zone_violation"), "duplicate"),
    (lambda d: d["sources"][0].update(points=150), "points"),
    (lambda d: d["sources"][0].update(points=12.5), "points"),
    (lambda d: d["sources"][0].update(points="lots"), "points"),
    (lambda d: d["sources"][0].update(label=""), "label"),
    (lambda d: d["sources"][0].update(match={}), "event_type"),
    (lambda d: d["sources"][0].update(match={"event_type": "X", "where": {"colour": "red"}}), "match.where key"),
    (lambda d: d["sources"][0].update(unknown=1), "unknown keys"),
    (lambda d: d["sources"][6].update(status_multiplier={"maybe": 1.0}), "status_multiplier"),
    (lambda d: d["sources"][6].update(status_multiplier={"review": 1.5}), "between 0 and 1"),
    (lambda d: d["sources"][5].update(excluded_by=["nope"]), "unknown source"),
    (lambda d: d["sources"][5].update(excluded_by=["line_crossing"]), "exclude each other"),
    (lambda d: d["sources"][0].update(max_occurrences=0), "max_occurrences"),
])
def test_invalid_scoring_sections_are_rejected(mutate, message):
    with pytest.raises(ValueError, match=message):
        parse_scoring_config(cfg_data(mutate))


def test_a_missing_section_is_reported():
    with pytest.raises(ValueError, match="no 'scoring' section"):
        parse_scoring_config({"rules": []})


def test_two_sources_that_exclude_each_other_are_rejected():
    def mutate(d):
        d["sources"][0]["excluded_by"] = ["direction_violation"]
        d["sources"][1]["excluded_by"] = ["zone_violation"]
    with pytest.raises(ValueError, match="exclude each other"):
        parse_scoring_config(cfg_data(mutate))


def test_event_matching_uses_attributes_and_details_with_any_of_lists():
    cfg = make_scoring()
    line = cfg.source("line_crossing")
    vehicle = cfg.source("watchlist_vehicle")
    assert source_matches(line, obs("LINE_CROSSING", 1.0, rule_id="L1", rule_type="tripwire", rule_kind="line", direction="IN"))
    assert not source_matches(line, obs("LINE_CROSSING", 1.0, rule_id="L1", rule_type="other", rule_kind="line"))
    assert not source_matches(line, obs("ZONE_ENTER", 1.0))
    hit = lambda etype: obs("WATCHLIST_MATCH", 1.0, rule_kind="watchlist", details={"entity_type": etype})
    assert source_matches(vehicle, hit("PLATE")) and source_matches(vehicle, hit("VEHICLE"))
    assert not source_matches(vehicle, hit("FACE"))
    assert not source_matches(vehicle, obs("WATCHLIST_MATCH", 1.0, rule_kind="watchlist"))       # field absent


def test_cross_check_between_scoring_and_behaviour_rules():
    scoring = make_scoring()
    rules = make_cfg([make_rule("R1", event_type="ZONE_VIOLATION"), make_rule("R9", event_type="BRAND_NEW_EVENT")])
    warnings = check_scoring_against_rules(scoring, rules)
    assert any("BRAND_NEW_EVENT" in w and "R9" in w for w in warnings)               # a rule nobody scores
    assert any("direction_violation" in w for w in warnings)                          # a source nothing produces
    assert not any("zone_violation" in w for w in warnings)


def test_the_shipped_scoring_section_matches_the_plan_table():
    path = app_config.CONFIG_DIR / "rules.json"
    if not path.exists() or "scoring" not in json.loads(path.read_text()):
        pytest.skip("configs/rules.json has no scoring section yet")
    cfg = load_scoring_config(path)
    assert cfg.max_score == 100 and [m for _, m in cfg.levels] == [0, 30, 60, 80]
    assert cfg.source("line_crossing").points == 20
    assert cfg.source("watchlist_vehicle").points == 40 and cfg.source("watchlist_person").points == 50
    assert cfg.bonus.points == 10
