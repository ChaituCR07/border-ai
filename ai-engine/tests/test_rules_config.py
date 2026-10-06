import pytest

from app.analytics.rules_config import parse_camera_rules


def base(**over):
    data = {"camera_id": "C1",
            "zones": [{"polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]}],
            "lines": [{"p1": [0, 0.5], "p2": [1, 0.5]}]}
    data.update(over)
    return data


def test_valid_config_gets_defaults_and_auto_ids():
    r = parse_camera_rules(base())
    assert r.zones[0].id == "Z1" and r.lines[0].id == "L1"
    assert r.zones[0].min_frames_inside == 3 and r.lines[0].positive_direction == "IN"
    assert r.min_track_hits == 3


def test_missing_camera_id():
    with pytest.raises(ValueError):
        parse_camera_rules({"zones": []})


def test_rejects_points_outside_unit_range():
    with pytest.raises(ValueError):
        parse_camera_rules(base(zones=[{"polygon": [[0, 0], [1.2, 0], [1, 1]]}]))


def test_rejects_too_few_points():
    with pytest.raises(ValueError):
        parse_camera_rules(base(zones=[{"polygon": [[0, 0], [1, 1]]}]))


def test_rejects_self_intersecting_polygon():
    bowtie = [[0, 0], [1, 1], [1, 0], [0, 1]]
    with pytest.raises(ValueError):
        parse_camera_rules(base(zones=[{"polygon": bowtie}]))


def test_rejects_zero_area_polygon():
    with pytest.raises(ValueError):
        parse_camera_rules(base(zones=[{"polygon": [[0, 0], [0.5, 0.5], [1, 1]]}]))


def test_rejects_duplicate_ids_across_zones_and_lines():
    data = base(zones=[{"id": "X", "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]]}],
                lines=[{"id": "X", "p1": [0, 0.5], "p2": [1, 0.5]}])
    with pytest.raises(ValueError):
        parse_camera_rules(data)


def test_rejects_bad_direction_and_identical_endpoints():
    with pytest.raises(ValueError):
        parse_camera_rules(base(lines=[{"p1": [0, 0.5], "p2": [1, 0.5], "positive_direction": "UP"}]))
    with pytest.raises(ValueError):
        parse_camera_rules(base(lines=[{"p1": [0.5, 0.5], "p2": [0.5, 0.5]}]))
