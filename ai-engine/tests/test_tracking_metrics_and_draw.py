from collections import Counter, deque

import numpy as np

from app.pipeline.visualizer import draw_tracks
from app.schemas.tracking import TrackedObject
from app.tracking.metrics import find_fragment_candidates, summarize_tracks
from app.tracking.track_store import Track, TrackStore


def make_track(tid, first, last, p_first, p_last, cls="person"):
    t = Track(track_id=tid, camera_id="A", first_seen=first, last_seen=last,
              first_tick=0, last_tick=0, first_point=p_first, trail=deque(maxlen=10))
    t.trail.append((last, *p_last))
    t.class_votes = Counter({cls: 1.0})
    return t


def test_fragment_candidate_detected():
    a = make_track(1, 0.0, 5.0, (0, 0), (300, 300))
    b = make_track(2, 5.5, 9.0, (310, 305), (500, 400))        # starts nearby right after a ends
    far = make_track(3, 5.5, 9.0, (900, 900), (950, 950))      # too far away
    pairs = find_fragment_candidates([a, b, far])
    assert (1, 2) in pairs and (1, 3) not in pairs


def test_summary_counts_short_tracks():
    tracks = [make_track(1, 0, 0.2, (0, 0), (1, 1)), make_track(2, 0, 8, (0, 0), (50, 50))]
    s = summarize_tracks(tracks)
    assert s["tracks"] == 2 and s["short_tracks"] == 1 and s["longest_s"] == 8


def test_draw_tracks_with_trails_and_lost_ghosts():
    store = TrackStore("A", max_lost_frames=5)
    img = np.zeros((360, 640, 3), np.uint8)
    for i in range(6):
        o = TrackedObject(1, 0, "person", 0.9, 100 + i * 5, 100, 140 + i * 5, 200)
        store.update([o], i * 0.1)
    store.update([], 0.7)                                      # track 1 becomes LOST
    live = TrackedObject(2, 2, "car", 0.8, 300, 200, 420, 280)
    out = draw_tracks(img, [live], store)
    assert out.shape == (360, 640, 3) and out.any()


def test_draw_tracks_label_at_image_edge_does_not_crash():
    img = np.zeros((100, 100, 3), np.uint8)
    draw_tracks(img, [TrackedObject(7, 0, "person", 0.5, 0, 0, 40, 60)])
