import pytest

from app.watchlist.config import WatchlistConfig
from app.watchlist.csv_io import export_csv, import_csv
from app.watchlist.repo import InMemoryWatchlistRepo


def test_defaults_are_valid_and_unknown_keys_are_ignored():
    cfg = WatchlistConfig.from_config({"cooldown_s": 5, "future_setting": 1})
    assert cfg.cooldown_s == 5 and cfg.alert_min_confidence == 0.70


@pytest.mark.parametrize("bad", [
    {"backend": "mongo"}, {"alert_min_confidence": 1.5}, {"min_score": 120},
    {"near_max_distance": -1}, {"queue_size": 0}, {"entity_types": []},
])
def test_invalid_configuration_is_rejected(bad):
    with pytest.raises(ValueError):
        WatchlistConfig(**bad)


def test_csv_import_reports_bad_rows_and_duplicates(tmp_path):
    f = tmp_path / "w.csv"
    f.write_text(
        "entity_type,identifier,name,risk_level,description\n"
        "VEHICLE,KA01AB1234,Vehicle A,HIGH,ok\n"
        "VEHICLE,ka-01-ab-1234,Vehicle A again,HIGH,duplicate of the first\n"
        "VEHICLE,A1,Too short,HIGH,\n"
        "PLATE,MH12XY4321,Plate B,MEDIUM,\n")
    repo = InMemoryWatchlistRepo()
    added, skipped, errors = import_csv(repo, f)
    assert (added, skipped) == (2, 1)
    assert len(errors) == 1 and errors[0].startswith("line 4")


def test_csv_import_requires_the_columns(tmp_path):
    f = tmp_path / "w.csv"
    f.write_text("identifier,name\nKA01AB1234,x\n")
    assert import_csv(InMemoryWatchlistRepo(), f)[2][0].startswith("missing columns")


def test_csv_round_trip(tmp_path):
    repo = InMemoryWatchlistRepo()
    repo.add("VEHICLE", "KA01AB1234", "Vehicle A", "HIGH", "d1")
    repo.add("PLATE", "MH12XY4321", "Plate B", "LOW")
    out = tmp_path / "out.csv"
    assert export_csv(repo, out) == 2
    again = InMemoryWatchlistRepo()
    assert import_csv(again, out)[:2] == (2, 0)
    assert [e.normalized_identifier for e in again.list_entries()] == ["KA01AB1234", "MH12XY4321"]
