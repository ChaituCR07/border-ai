from app.tracking.interpolator import interpolate_trail


def test_interpolate_empty_or_single_point():
    assert interpolate_trail([]) == []
    assert interpolate_trail([(0.0, 10.0, 20.0)]) == [(0.0, 10.0, 20.0)]


def test_interpolate_linear_bridge():
    points = [(0.0, 0.0, 0.0), (0.2, 20.0, 40.0)]
    interp = interpolate_trail(points, max_time_gap_s=0.5, step_time_s=0.05)
    # Gaps of 0.05s: 0.0, 0.05, 0.10, 0.15, 0.20
    assert len(interp) == 5
    assert interp[0] == (0.0, 0.0, 0.0)
    assert interp[1] == (0.05, 5.0, 10.0)
    assert interp[2] == (0.10, 10.0, 20.0)
    assert interp[3] == (0.15, 15.0, 30.0)
    assert interp[4] == (0.2, 20.0, 40.0)


def test_interpolate_skips_large_gap():
    # Gap larger than max_time_gap_s is not interpolated
    points = [(0.0, 0.0, 0.0), (2.0, 100.0, 100.0)]
    interp = interpolate_trail(points, max_time_gap_s=0.5)
    assert len(interp) == 2
