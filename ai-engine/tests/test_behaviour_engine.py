import json
import os
import threading

from app.behaviour.engine import BehaviourEngine
from app.behaviour.rules_config import load_behaviour_config
from behaviour_helpers import Scene, make_cfg, make_rule, obs

ZONE = [{"type": "object", "value": ["person", "car"]}, {"type": "zone", "zone_type": "restricted"}]


def zone_rule(**kw):
    return make_rule("R1", ZONE, "ZONE_VIOLATION", "HIGH", 30, **kw)


def test_fires_once_when_the_conditions_become_true_and_never_before():
    s = Scene([zone_rule()])
    assert s.step() == []                                           # not in the zone yet
    out = s.step(events=[obs("ZONE_ENTER", s.t)])
    assert [e.type for e in out] == ["ZONE_VIOLATION"]
    e = out[0]
    assert (e.details["severity"], e.details["points"], e.rule_kind, e.rule_id) == ("HIGH", 30, "behaviour", "R1")
    assert e.to_dict()["severity"] == "HIGH" and e.to_dict()["event"] == "ZONE_VIOLATION"
    assert any("restricted" in r for r in e.details["reasons"]) and e.details["bindings"] == {"zone_id": "Z1"}
    assert s.run(30) == []                                          # still inside: no repeat


def test_it_can_fire_again_after_the_condition_was_false_for_rearm_s():
    s = Scene([zone_rule(rearm_s=30)])
    s.step(events=[obs("ZONE_ENTER", s.t)])
    s.step(events=[obs("ZONE_EXIT", s.t)])
    assert s.step(events=[obs("ZONE_ENTER", s.t)]) == []             # re-entered too quickly (inside rearm_s)
    s.step(events=[obs("ZONE_EXIT", s.t)])
    s.run(40)                                                       # false for longer than rearm_s
    assert len(s.step(events=[obs("ZONE_ENTER", s.t)])) == 1


def test_cooldown_limits_firing_per_track_and_rule():
    s = Scene([zone_rule(cooldown_s=300, rearm_s=0)])
    assert len(s.step(events=[obs("ZONE_ENTER", s.t)])) == 1
    s.step(events=[obs("ZONE_EXIT", s.t)])
    s.run(100)
    assert s.step(events=[obs("ZONE_ENTER", s.t)]) == [] and s.engine.stats["suppressed_cooldown"] == 1
    s.step(events=[obs("ZONE_EXIT", s.t)])
    s.run(250)
    assert len(s.step(events=[obs("ZONE_ENTER", s.t)])) == 1


def test_each_zone_is_its_own_episode():
    rule = make_rule("R3", [{"type": "zone", "zone_type": "any", "min_dwell_s": 5}], "LOITERING_VIOLATION", "MEDIUM", 15)
    s = Scene([rule])
    s.step(events=[obs("ZONE_ENTER", s.t, rule_id="Z1", rule_type="restricted"),
                   obs("ZONE_ENTER", s.t, rule_id="Z2", rule_type="monitored")])
    out = s.run(8)
    assert sorted(e.details["bindings"]["zone_id"] for e in out) == ["Z1", "Z2"]


def test_every_crossing_is_its_own_episode():
    rule = make_rule("R2", [{"type": "line_crossing", "line": "L1", "expected_direction": "IN", "within_s": 5}],
                     "DIRECTION_VIOLATION", "MEDIUM", 20)
    s = Scene([rule])
    assert s.step(events=[obs("LINE_CROSSING", s.t, rule_id="L1", rule_kind="line", rule_type="tripwire", direction="IN")]) == []
    assert len(s.step(events=[obs("LINE_CROSSING", s.t, rule_id="L1", rule_kind="line", rule_type="tripwire", direction="OUT")])) == 1
    assert s.run(30) == []                                          # the same crossing is not reported twice
    assert len(s.step(events=[obs("LINE_CROSSING", s.t, rule_id="L1", rule_kind="line", rule_type="tripwire", direction="OUT")])) == 1


def test_camera_filter_and_disabled_rules():
    s = Scene([zone_rule(cameras=["OTHER"]), make_rule("R9", ZONE, "NEVER_FIRES", enabled=False)])
    assert s.step(events=[obs("ZONE_ENTER", s.t)]) == []
    assert s.engine.status()["rules"] == 1


def test_tracks_are_independent():
    s = Scene([zone_rule()])
    out = s.step(tracks=((1, "person"), (2, "person")), events=[obs("ZONE_ENTER", s.t, track=2)])
    assert [e.track_id for e in out] == [2]


def test_state_is_forgotten_when_a_track_is_removed():
    s = Scene([zone_rule()])
    s.step(events=[obs("ZONE_ENTER", s.t)])
    assert s.engine.status()["contexts"] == 1
    s.step(tracks=(), removed=[1])
    assert s.engine.status()["contexts"] == 0 and s.engine._active == {} and s.engine._last_fire == {}


def test_contexts_that_never_appear_in_a_frame_are_pruned():
    s = Scene([zone_rule()], dt=100.0)
    s.step(tracks=(), events=[obs("ZONE_ENTER", s.t, track=99)])         # an observation for a track we never see
    s.run(10, tracks=())                                                  # 1000 s pass
    assert s.engine.status()["contexts"] == 0 and s.engine.stats["pruned_contexts"] == 1


def test_behaviour_events_are_not_fed_back_into_the_engine():
    s = Scene([zone_rule()])
    s.engine.observe("CAM", [obs("ZONE_VIOLATION", s.t, rule_id="R1", rule_kind="behaviour")])
    assert s.engine._inbox == {}


def test_observe_is_thread_safe():
    s = Scene([zone_rule()])

    def feed(track):
        for i in range(100):
            s.engine.observe("CAM", [obs("LINE_CROSSING", s.t, track=track, rule_id="L1", rule_kind="line", direction="IN")])

    threads = [threading.Thread(target=feed, args=(t,)) for t in range(1, 9)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    s.step(tracks=tuple((t, "person") for t in range(1, 9)))
    assert s.engine.status()["contexts"] == 8


def test_a_failing_rule_is_isolated(monkeypatch):
    import app.behaviour.engine as engine_module
    real = engine_module.evaluate_all

    def flaky(conditions, ctx, env):
        if conditions and conditions[0].get("value") == ["boom"]:
            raise RuntimeError("bug")
        return real(conditions, ctx, env)

    monkeypatch.setattr(engine_module, "evaluate_all", flaky)
    bad = make_rule("BAD", [{"type": "object", "value": "boom"}], "BAD_RULE")
    s = Scene([bad, zone_rule()])
    out = s.step(events=[obs("ZONE_ENTER", s.t)])
    assert [e.type for e in out] == ["ZONE_VIOLATION"] and s.engine.stats["errors"] == 1
    s.step()
    assert s.engine.stats["errors"] == 1                                  # the broken rule is not retried every frame


def test_hot_reload_applies_valid_files_and_ignores_invalid_ones(tmp_path):
    path = tmp_path / "rules.json"
    good = {"version": 1, "site": {"timezone": "UTC"}, "rules": [zone_rule()]}
    path.write_text(json.dumps(good))
    engine = BehaviourEngine(load_behaviour_config(path), rules_path=path, reload_check_s=0)
    assert engine.status()["rules"] == 1

    new = {"version": 1, "site": {"timezone": "UTC"}, "rules": [zone_rule(), make_rule("R2", ZONE, "SECOND_RULE")]}
    path.write_text(json.dumps(new))
    mtime = path.stat().st_mtime + 10
    os.utime(path, (mtime, mtime))
    engine.maybe_reload()
    assert engine.status()["rules"] == 2 and engine.stats["reloads"] == 1

    path.write_text("{ this is not json")
    os.utime(path, (mtime + 10, mtime + 10))
    engine.maybe_reload()
    assert engine.status()["rules"] == 2 and engine.stats["reload_errors"] == 1     # the old rules keep working
