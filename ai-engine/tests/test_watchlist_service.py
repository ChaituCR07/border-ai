import json

from app.schemas.events import PLATE_RECOGNIZED, WATCHLIST_MATCH, Event
from app.schemas.tracking import TrackedObject
from app.watchlist.config import WatchlistConfig
from app.watchlist.repo import InMemoryWatchlistRepo
from app.watchlist.service import WatchlistService


def plate_event(plate="KA01AB1234", conf=0.91, track=1, cam="CAM", ts=0.0, final=False):
    return Event(type=PLATE_RECOGNIZED, camera_id=cam, timestamp=ts, frame_id=10, track_id=track,
                 object_class="car", confidence=conf, bbox=(60.0, 60.0, 260.0, 160.0), rule_id="ANPR",
                 rule_name="Plate recognition", rule_kind="anpr", rule_type="plate",
                 details={"plate": plate, "final": final})


def make(entries=(("VEHICLE", "KA01AB1234", "HIGH"),), block=True, **cfg_kw):
    repo = InMemoryWatchlistRepo()
    for etype, ident, risk in entries:
        repo.add(etype, ident, "SECRET NAME", risk, "SECRET DESCRIPTION", actor="test")
    svc = WatchlistService(repo, WatchlistConfig(**cfg_kw))
    out = []
    svc.attach(emit=lambda cid, ev: out.extend(ev), block_when_full=block)
    svc.refresh_snapshot()
    return svc, repo, out


def push(svc, event):
    svc.submit(event)
    svc.run_pending()


def test_exact_match_raises_an_alert_with_the_planned_fields():
    svc, repo, out = make()
    push(svc, plate_event())
    assert len(out) == 1
    e = out[0]
    assert e.type == WATCHLIST_MATCH
    d = e.to_dict()
    assert d["type"] == "WATCHLIST_MATCH" and d["plate"] == "KA01AB1234" and d["score"] == 91
    assert d["track_id"] == 1 and d["camera_id"] == "CAM" and d["timestamp"].endswith("Z")
    assert d["details"]["status"] == "alert" and d["details"]["risk_level"] == "HIGH"
    assert d["details"]["match_type"] == "exact" and d["details"]["review_required"] is False


def test_unlisted_plate_produces_nothing():
    svc, repo, out = make()
    push(svc, plate_event("MH12XY4321"))
    assert out == [] and svc.stats["no_match"] == 1 and repo.recent_hits() == []


def test_low_confidence_exact_match_needs_review():
    svc, _, out = make()
    push(svc, plate_event(conf=0.5))
    assert out[0].details["status"] == "review" and out[0].details["review_required"] is True
    assert out[0].details["score"] == 50


def test_very_weak_match_is_not_recorded_at_all():
    svc, repo, out = make()
    push(svc, plate_event(conf=0.3))                      # score 30 < min_score 40
    assert out == [] and svc.stats["below_min_score"] == 1 and repo.recent_hits() == []


def test_near_match_is_review_by_default_and_can_alert_when_enabled():
    svc, _, out = make()
    push(svc, plate_event("KA01AB1284", conf=0.95))
    assert out[0].details["match_type"] == "near" and out[0].details["status"] == "review"
    assert out[0].details["score"] == 76 and out[0].details["matched_identifier"] == "KA01AB1234"

    svc2, _, out2 = make(near_can_alert=True)
    push(svc2, plate_event("KA01AB1284", conf=0.95))
    assert out2[0].details["status"] == "alert"


def test_near_matching_can_be_switched_off():
    svc, _, out = make(near_max_distance=0)
    push(svc, plate_event("KA01AB1284", conf=0.95))
    assert out == []


def test_same_track_and_plate_is_looked_up_once_but_a_changed_plate_is_looked_up_again():
    svc, _, out = make()
    push(svc, plate_event(track=1))
    push(svc, plate_event(track=1, final=True))                 # same plate text: skipped
    assert len(out) == 1 and svc.stats["skipped_repeat"] == 1
    push(svc, plate_event("MH12XY4321", track=1, final=True))   # changed plate: new lookup, no match
    assert svc.stats["no_match"] == 1


def test_cooldown_suppresses_repeats_but_stores_them():
    svc, repo, out = make(cooldown_s=60)
    push(svc, plate_event(track=1, ts=100.0))
    push(svc, plate_event(track=2, ts=130.0))                   # another track, 30 s later
    assert len(out) == 1 and svc.stats["suppressed"] == 1
    assert [h["status"] for h in repo.recent_hits()] == ["suppressed", "alert"]
    push(svc, plate_event(track=3, ts=170.0))                   # 70 s after the last alert
    assert len(out) == 2


def test_cooldown_is_per_camera_and_per_entry():
    svc, _, out = make(entries=(("VEHICLE", "KA01AB1234", "HIGH"), ("VEHICLE", "MH12XY4321", "LOW")))
    push(svc, plate_event("KA01AB1234", track=1, cam="CAM_A", ts=10.0))
    push(svc, plate_event("KA01AB1234", track=2, cam="CAM_B", ts=11.0))     # other camera: allowed
    push(svc, plate_event("MH12XY4321", track=3, cam="CAM_A", ts=12.0))     # other entry: allowed
    assert len(out) == 3


def test_a_stronger_status_gets_through_the_cooldown():
    svc, _, out = make(cooldown_s=60)
    push(svc, plate_event(conf=0.5, track=1, ts=10.0))          # review
    push(svc, plate_event(conf=0.95, track=2, ts=20.0))         # alert, inside the cooldown
    assert [e.details["status"] for e in out] == ["review", "alert"]


def test_highest_risk_entry_is_reported_and_others_are_listed():
    svc, _, out = make(entries=(("PLATE", "KA01AB1234", "LOW"), ("VEHICLE", "KA01AB1234", "CRITICAL")))
    push(svc, plate_event())
    d = out[0].details
    assert d["risk_level"] == "CRITICAL" and d["entity_type"] == "VEHICLE" and len(d["also_matched"]) == 1
    assert out[0].rule_type == "vehicle"


def test_only_configured_entity_types_are_matched():
    svc, _, out = make(entries=(("PERSON", "KA01AB1234x", "HIGH"),))
    push(svc, plate_event())
    assert out == []


def test_new_and_deactivated_entries_take_effect_immediately():
    svc, repo, out = make(entries=())
    push(svc, plate_event(track=1))
    assert out == []
    e = repo.add("VEHICLE", "KA01AB1234", "N", "HIGH")
    push(svc, plate_event(track=2, ts=500.0))
    assert len(out) == 1
    repo.deactivate(e.watchlist_id)
    push(svc, plate_event(track=3, ts=1000.0))
    assert len(out) == 1


def test_flags_follow_the_track_and_clear_when_it_ends():
    svc, _, _ = make()
    push(svc, plate_event(track=5))
    assert svc.flags_snapshot("CAM") == {5: "HIGH"} and svc.flags_snapshot("OTHER") == {}
    svc.on_tracks_removed("CAM", [TrackedObject(5, 0, "car", 0.9, 0, 0, 1, 1)])
    assert svc.flags_snapshot("CAM") == {}


def test_review_flag_text():
    svc, _, _ = make()
    push(svc, plate_event(conf=0.5, track=5))
    assert svc.flags_snapshot("CAM") == {5: "HIGH REVIEW"}


def test_hits_are_persisted_with_the_event_id():
    svc, repo, out = make()
    push(svc, plate_event(track=9))
    row = repo.recent_hits()[0]
    assert row["status"] == "alert" and row["track_id"] == 9 and row["event_id"] == out[0].event_id


def test_database_outage_falls_back_to_the_snapshot_and_saves_hits_later():
    svc, repo, out = make()
    repo.fail = True                                           # the snapshot was loaded before the outage
    push(svc, plate_event())
    assert len(out) == 1 and out[0].details["status"] == "alert"
    st = svc.status()
    assert st["db_ok"] is False and st["fallback_lookups"] == 1 and st["hits_unsaved"] == 1
    repo.fail = False
    svc.run_housekeeping(force=True)
    assert svc.status()["hits_unsaved"] == 0 and len(repo.recent_hits()) == 1


def test_outage_before_any_snapshot_is_reported_without_crashing():
    repo = InMemoryWatchlistRepo()
    repo.fail = True
    svc = WatchlistService(repo, WatchlistConfig())
    out = []
    svc.attach(emit=lambda cid, ev: out.extend(ev), block_when_full=True)
    assert svc.refresh_snapshot() is False
    push(svc, plate_event())
    assert out == [] and svc.status()["db_ok"] is False


def test_non_plate_events_are_ignored():
    svc, _, out = make()
    ignored = Event(type="LINE_CROSSING", camera_id="C", timestamp=0.0, frame_id=1, track_id=1,
                    object_class="person", confidence=0.9, bbox=(0, 0, 1, 1), rule_id="L1",
                    rule_name="x", rule_kind="line", rule_type="tripwire")
    assert svc.submit(ignored) is False and out == []


def test_live_mode_drops_when_the_queue_is_full():
    svc, _, _ = make(block=False, queue_size=1, submit_timeout_s=0.05)
    assert svc.submit(plate_event(track=1)) is True
    assert svc.submit(plate_event(track=2)) is False
    assert svc.stats["dropped"] == 1


def test_events_never_contain_the_entry_name_or_description():
    svc, _, out = make()
    push(svc, plate_event())
    blob = json.dumps(out[0].to_dict())
    assert "SECRET NAME" not in blob and "SECRET DESCRIPTION" not in blob


def test_worker_thread_processes_jobs_and_stops_cleanly():
    svc, _, out = make()
    svc.start()
    svc.submit(plate_event())
    svc.stop(drain=True)
    assert len(out) == 1
    svc.stop(drain=True)                                       # calling stop twice is safe
