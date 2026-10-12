from app.anpr.metrics import char_accuracy, evaluate_records, levenshtein
from app.anpr.types import PlateRecord


def rec(plate, first, last, conf=0.9, reads=None):
    return PlateRecord("C", 1, plate, conf, 5, 4, 0.8, "strict", True, "car", first, last,
                       read_log=reads or [])


def test_levenshtein_and_char_accuracy():
    assert levenshtein("KA01AB1234", "KA01AB1284") == 1
    assert abs(char_accuracy("KA01AB1284", "KA01AB1234") - 0.9) < 1e-9
    assert char_accuracy("", "KA01AB1234") == 0.0


def test_evaluate_matches_by_time_window():
    truth = [{"plate": "KA01AB1234", "first_s": 3, "last_s": 9},
             {"plate": "MH12XY4321", "first_s": 14, "last_s": 20}]
    records = [rec("KA01AB1234", 3.5, 9.0, reads=[("KA01AB1234", 0.9), ("KA01AB1284", 0.8)]),
               rec("MH12XY4351", 14.2, 19.0, conf=0.6),
               rec("ZZ99ZZ9999", 40.0, 45.0)]                      # not in any window: an extra
    rep = evaluate_records(records, truth)
    assert rep["exact"] == 1 and rep["plate_accuracy"] == 0.5
    assert rep["extras"] == 1 and rep["missed"] == 0
    assert rep["rows"][0]["single_read_acc"] == 0.5
    assert 0.8 < rep["mean_char_accuracy"] < 1.0
    assert rep["mean_conf_when_correct"] == 0.9 and rep["mean_conf_when_wrong"] == 0.6


def test_missed_vehicle_counts_as_zero():
    rep = evaluate_records([], [{"plate": "KA01AB1234", "first_s": 3, "last_s": 9}])
    assert rep["missed"] == 1 and rep["plate_accuracy"] == 0.0
