import numpy as np

from app.analytics.geometry import crossing_within_segment, point_in_polygon, signed_distance

P1, P2 = (0.0, 240.0), (640.0, 240.0)           # horizontal line, left to right


def test_signed_distance_sign_convention():
    assert signed_distance((100, 300), P1, P2) > 0      # below the line (y grows downward)
    assert signed_distance((100, 100), P1, P2) < 0      # above
    assert abs(signed_distance((100, 240), P1, P2)) < 1e-9


def test_crossing_inside_segment():
    assert crossing_within_segment((320, 230), (320, 250), -10.0, 10.0, P1, P2)


def test_crossing_outside_segment_extent_is_rejected():
    short1, short2 = (200.0, 240.0), (400.0, 240.0)
    d_ref, d_cur = signed_distance((600, 230), short1, short2), signed_distance((600, 250), short1, short2)
    assert not crossing_within_segment((600, 230), (600, 250), d_ref, d_cur, short1, short2)


def test_point_in_polygon():
    poly = np.array([[100, 100], [300, 100], [300, 300], [100, 300]], np.float32).reshape(-1, 1, 2)
    assert point_in_polygon((200, 200), poly)
    assert not point_in_polygon((50, 50), poly)
    assert point_in_polygon((100, 200), poly)           # on the edge counts as inside
