from types import SimpleNamespace

from app.db.events_repo import InMemoryEventRepository
from app.db.seed import camera_row
from app.pipeline.track_summary import track_summary_event
from db_helpers import T0, to_record, utc, zone_event


def cfg(**kw):
    base = dict(camera_id="CAM_001", name="Demo Gate Camera", location="North gate", source_type="rtsp",
                source="rtsp://admin:s3cret@10.0.0.5:554/stream1", enabled=True, target_fps=10)
    base.update(kw)
    return SimpleNamespace(**base)


def test_seeded_cameras_never_carry_credentials():
    row = camera_row(cfg())
    assert "s3cret" not in row["rtsp_url"] and "admin" not in row["rtsp_url"] and row["status"] == "ACTIVE"
    repo = InMemoryEventRepository()
    repo.upsert_camera(**row)                                                       # the row is accepted by the schema rules
    assert repo.get_camera("CAM_001")["location"] == "North gate"


def test_file_sources_have_no_url_and_disabled_cameras_are_inactive():
    row = camera_row(cfg(source_type="file", source="videos/demo.mp4", enabled=False))
    assert row["rtsp_url"] is None and row["status"] == "INACTIVE" and row["metadata"]["source_type"] == "file"


def track(hits=30, first=T0, last=T0 + 9.0):
    return SimpleNamespace(track_id=7, hits=hits, first_seen=first, last_seen=last, dominant_class="person",
                           last_confidence=0.83, last_bbox=(10, 20, 110, 220))


def test_a_track_summary_event_describes_the_track():
    e = track_summary_event(track(), "CAM_1", frame_id=99, min_hits=5)
    assert e.type == "TRACK_SUMMARY" and e.track_id == 7 and e.object_class == "person" and e.timestamp == T0 + 9.0
    d = e.details
    assert d["hits"] == 30 and d["duration_s"] == 9.0 and d["first_seen"].endswith("Z") and d["last_seen"].endswith("Z")
    rec = to_record(e)
    assert rec.detection.object_type == "person" and rec.detection.hits == 30


def test_flickering_tracks_are_not_summarized():
    assert track_summary_event(track(hits=4), "CAM_1", 1, min_hits=5) is None


def test_retention_deletes_by_policy_and_reports():
    repo = InMemoryEventRepository()
    repo.upsert_camera("CAM_1", "Gate")
    old, new = zone_event(0), zone_event(0, ts=T0 + 90 * 86400)
    for e in (old, new):
        repo.store(to_record(e))
    deleted = repo.purge(utc(T0 + 30 * 86400), utc(T0 + 30 * 86400))
    assert deleted == {"alerts": 0, "events": 1} and repo.get_event(old.event_id) is None and repo.get_event(new.event_id)
