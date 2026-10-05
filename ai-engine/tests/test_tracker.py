from app.schemas.detection import Detection, FrameDetections
from app.tracking.manager import MultiCameraTracker
from app.tracking.tracker import TrackerParams


def det(x1, y1, x2, y2, conf=0.9):
    return Detection(0, "person", conf, x1, y1, x2, y2)


def fd(cam, i, dets):
    return FrameDetections(cam, i, float(i), 640, 480, dets)


def make():
    return MultiCameraTracker({0: "person"}, TrackerParams(), default_fps=30)


def test_single_moving_object_keeps_one_id():
    mt = make()
    ids = set()
    for i in range(1, 31):
        ft, _ = mt.update(fd("A", i, [det(100 + 5 * i, 200, 140 + 5 * i, 300)]))
        ids.update(o.track_id for o in ft.tracks)
    assert len(ids) == 1


def test_two_separated_objects_get_two_ids():
    mt = make()
    ids = set()
    for i in range(1, 21):
        ft, _ = mt.update(fd("A", i, [det(50 + 3 * i, 100, 90 + 3 * i, 200),
                                      det(400 - 3 * i, 250, 440 - 3 * i, 350)]))
        ids.update(o.track_id for o in ft.tracks)
    assert len(ids) == 2


def test_object_returning_after_buffer_gets_a_new_id():
    mt = make()                                           # 30 FPS, buffer 30 -> 30 lost frames
    before = set()
    for i in range(1, 6):
        ft, _ = mt.update(fd("A", i, [det(100, 200, 140, 300)]))
        before.update(o.track_id for o in ft.tracks)
    for i in range(6, 46):                                # 40 empty frames > 30
        mt.update(fd("A", i, []))
    after = set()
    for i in range(46, 51):
        ft, _ = mt.update(fd("A", i, [det(100, 200, 140, 300)]))
        after.update(o.track_id for o in ft.tracks)
    assert after and not (after & before)


def test_cameras_have_independent_state():
    mt = make()
    for i in range(1, 6):
        mt.update(fd("A", i, [det(100, 200, 140, 300)]))
        mt.update(fd("B", i, [det(300, 100, 340, 200)]))
    assert mt.store("A") is not mt.store("B")
    assert len(mt.store("A").active_tracks()) == 1
    assert len(mt.store("B").active_tracks()) == 1
    assert mt.store("A").camera_id == "A" and mt.store("B").camera_id == "B"


def test_empty_frames_do_not_crash():
    mt = make()
    ft, upd = mt.update(fd("A", 1, []))
    assert ft.tracks == [] and upd.new == []
