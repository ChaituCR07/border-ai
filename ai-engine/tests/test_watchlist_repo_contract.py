import threading
from datetime import datetime, timezone

import pytest

from app.watchlist.models import (DuplicateEntry, EntryNotFound, InvalidEntry, WatchlistHit)
from app.watchlist.normalize import normalize_plate

TYPES = ("VEHICLE", "PLATE")


def add(repo, ident="KA01AB1234", etype="VEHICLE", risk="HIGH", name="Watchlist Vehicle 01", **kw):
    return repo.add(etype, ident, name, risk, actor="tester", **kw)


def hit(entry_id, **kw):
    base = dict(watchlist_id=entry_id, camera_id="CAM_1", track_id=7, plate="KA01AB1234",
                match_type="exact", distance=0.0, plate_confidence=0.91, score=91, status="alert",
                seen_at=datetime.now(timezone.utc), event_id="abc123")
    base.update(kw)
    return WatchlistHit(**base)


def test_add_and_get_normalizes_the_identifier(repo):
    e = add(repo, "ka-01 ab 1234")
    assert e.normalized_identifier == "KA01AB1234" and e.identifier == "ka-01 ab 1234"
    assert e.active and e.created_by == "tester" and e.watchlist_id >= 1
    assert repo.get(e.watchlist_id).name == "Watchlist Vehicle 01"


def test_get_unknown_entry(repo):
    with pytest.raises(EntryNotFound):
        repo.get(99999)


def test_duplicate_active_entry_is_rejected_even_when_formatted_differently(repo):
    add(repo, "KA01AB1234")
    with pytest.raises(DuplicateEntry):
        add(repo, "ka 01 ab 1234")


def test_same_plate_is_allowed_under_different_types(repo):
    add(repo, "KA01AB1234", "VEHICLE")
    add(repo, "KA01AB1234", "PLATE")
    assert len(repo.find_exact("KA01AB1234", TYPES)) == 2


def test_list_filters_by_type_and_active(repo):
    a = add(repo, "KA01AB1234")
    b = add(repo, "MH12XY4321", "PLATE")
    repo.deactivate(a.watchlist_id, actor="tester")
    assert [e.watchlist_id for e in repo.list_entries()] == [b.watchlist_id]
    assert len(repo.list_entries(active_only=False)) == 2
    assert repo.list_entries(entity_types=["VEHICLE"]) == []
    assert [e.watchlist_id for e in repo.list_entries(entity_types=["PLATE"])] == [b.watchlist_id]


def test_deactivate_hides_the_entry_and_frees_the_identifier(repo):
    e = add(repo)
    repo.deactivate(e.watchlist_id, actor="tester", reason="closed")
    assert repo.find_exact("KA01AB1234", TYPES) == []
    again = add(repo)                                              # allowed: the old one is inactive
    assert again.watchlist_id != e.watchlist_id


def test_deactivate_is_idempotent_and_unknown_ids_are_reported(repo):
    e = add(repo)
    repo.deactivate(e.watchlist_id)
    assert repo.deactivate(e.watchlist_id).active is False
    with pytest.raises(EntryNotFound):
        repo.deactivate(99999)


def test_restore_conflicts_with_an_active_duplicate(repo):
    first = add(repo)
    repo.deactivate(first.watchlist_id)
    add(repo)
    with pytest.raises(DuplicateEntry):
        repo.restore(first.watchlist_id)


def test_restore_brings_the_entry_back(repo):
    e = add(repo)
    repo.deactivate(e.watchlist_id)
    assert repo.restore(e.watchlist_id).active
    assert len(repo.find_exact("KA01AB1234", TYPES)) == 1


def test_update_changes_fields_and_validates(repo):
    e = add(repo)
    u = repo.update(e.watchlist_id, actor="tester", risk_level="low", name="Renamed")
    assert (u.risk_level, u.name) == ("LOW", "Renamed") and u.updated_at >= e.updated_at
    with pytest.raises(InvalidEntry):
        repo.update(e.watchlist_id, risk_level="SEVERE")
    with pytest.raises(InvalidEntry):
        repo.update(e.watchlist_id, normalized_identifier="X")
    with pytest.raises(EntryNotFound):
        repo.update(99999, name="x")


def test_audit_log_records_every_change_newest_first(repo):
    e = add(repo)
    repo.update(e.watchlist_id, actor="alice", name="N2")
    repo.deactivate(e.watchlist_id, actor="bob", reason="r")
    repo.restore(e.watchlist_id, actor="carol")
    log = repo.audit_log()
    assert [a["action"] for a in log] == ["RESTORE", "DEACTIVATE", "UPDATE", "ADD"]
    assert [a["actor"] for a in log] == ["carol", "bob", "alice", "tester"]
    assert all(a["watchlist_id"] == e.watchlist_id for a in log)


def test_find_exact_respects_types_and_active(repo):
    e = add(repo, etype="PLATE")
    assert repo.find_exact("KA01AB1234", ["VEHICLE"]) == []
    assert [x.watchlist_id for x in repo.find_exact("KA01AB1234", ["PLATE"])] == [e.watchlist_id]
    repo.deactivate(e.watchlist_id)
    assert repo.find_exact("KA01AB1234", ["PLATE"]) == []


def test_find_same_length_returns_only_that_length_and_honours_the_limit(repo):
    add(repo, "KA01AB1234")                 # 10 characters
    add(repo, "MH12XY4321")                 # 10 characters
    add(repo, "ABC1234")                    # 7 characters
    assert len(repo.find_same_length("ZZ99ZZ9999", TYPES)) == 2
    assert len(repo.find_same_length("ZZ99ZZ9999", TYPES, limit=1)) == 1
    assert len(repo.find_same_length("XYZ9999", TYPES)) == 1
    assert repo.find_same_length("ZZ9", TYPES) == []


def test_load_active_returns_only_requested_active_types(repo):
    a = add(repo, "KA01AB1234", "VEHICLE")
    add(repo, "MH12XY4321", "PLATE")
    repo.add("PERSON", "case ref 17", "Person", "LOW", actor="tester")
    repo.deactivate(a.watchlist_id)
    assert [e.entity_type for e in repo.load_active(TYPES)] == ["PLATE"]


def test_hits_are_stored_and_listed_newest_first(repo):
    e = add(repo)
    repo.record_hit(hit(e.watchlist_id, track_id=1, status="alert"))
    repo.record_hit(hit(e.watchlist_id, track_id=2, status="suppressed", event_id=None))
    rows = repo.recent_hits()
    assert [r["track_id"] for r in rows] == [2, 1]
    assert rows[0]["status"] == "suppressed" and rows[0]["event_id"] is None
    assert rows[1]["score"] == 91 and rows[1]["plate_confidence"] == pytest.approx(0.91, abs=1e-6)
    assert len(repo.recent_hits(limit=1)) == 1
    assert len(repo.recent_hits(watchlist_id=e.watchlist_id)) == 2


def test_a_hit_needs_an_existing_entry(repo):
    with pytest.raises(EntryNotFound):
        repo.record_hit(hit(99999))


def test_ping_succeeds(repo):
    repo.ping()


def test_sql_injection_strings_are_only_data(repo):
    nasty = "'); DROP TABLE watchlist;--"
    e = add(repo, name=nasty)
    assert repo.get(e.watchlist_id).name == nasty
    assert repo.find_exact("X' OR '1'='1", TYPES) == []
    assert repo.find_same_length("X' OR '1'='1", TYPES) == []
    with pytest.raises(InvalidEntry):
        add(repo, "KA01AB1234'; DROP TABLE watchlist;--")
    assert len(repo.list_entries()) == 1                 # the table is intact


def test_normalization_matches_the_lookup_key(repo):
    add(repo, "ka-01 ab 1234")
    assert len(repo.find_exact(normalize_plate("KA 01 AB 1234"), TYPES)) == 1


def test_concurrent_adds_of_different_plates_all_succeed(repo):
    plates = [f"KA{i:02d}AB{1000 + i}" for i in range(1, 21)]
    errors = []

    def worker(p):
        try:
            add(repo, p)
        except Exception as e:                           # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(p,)) for p in plates]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == [] and len(repo.list_entries()) == 20


def test_concurrent_adds_of_the_same_plate_allow_exactly_one(repo):
    results = []

    def worker():
        try:
            add(repo, "KA01AB1234")
            results.append("ok")
        except DuplicateEntry:
            results.append("duplicate")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("ok") == 1 and results.count("duplicate") == 7
