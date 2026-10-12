import numpy as np

from app.anpr.consensus import PlateConsensus
from app.anpr.types import PlateRead


def read(text, conf=0.9, weight=None, crop=None):
    return PlateRead(text=text, raw=text, confidence=conf, weight=weight or conf, quality=1.0,
                     level="strict", frame_id=0, timestamp=0.0, crop=crop)


def make(**kw):
    return PlateConsensus(lambda t: (t, "strict"), **kw)


def test_plan_example_one_bad_read_is_outvoted():
    c = make()
    for t in ["KA01AB1234"] * 2 + ["KA01AB1284"] + ["KA01AB1234"] * 2:
        c.add(read(t))
    r = c.best()
    assert r.text == "KA01AB1234" and r.votes == 4 and r.n_reads == 5
    assert r.method == "exact" and abs(r.agreement - 0.8) < 1e-9
    assert c.is_stable(r)


def test_character_vote_repairs_a_plate_no_single_read_contains():
    c = make()
    for t in ["KA01AB1634", "KA01AB1294", "KA01A81234"]:    # each read has a different wrong character
        c.add(read(t))
    r = c.best()
    assert r.text == "KA01AB1234" and r.method == "char"


def test_not_stable_with_too_few_reads():
    c = make(min_reads=3)
    c.add(read("KA01AB1234"))
    c.add(read("KA01AB1234"))
    assert not c.is_stable()


def test_not_stable_when_reads_disagree_completely():
    c = make()
    for t in ["AAAAAAAAAA", "BBBBBBBBBB", "CCCCCCCCCC"]:
        c.add(read(t))
    assert not c.is_stable()


def test_invalid_format_is_never_stable():
    c = PlateConsensus(lambda t: (t, "invalid"))
    for _ in range(5):
        c.add(PlateRead("HELLO", "HELLO", 0.9, 0.9, 1.0, "invalid", 0, 0.0))
    assert not c.is_stable()


def test_best_crop_is_the_highest_weight_read():
    c = make()
    low, high = np.zeros((4, 4, 3), np.uint8), np.ones((4, 4, 3), np.uint8)
    c.add(read("KA01AB1234", weight=0.2, crop=low))
    c.add(read("KA01AB1234", weight=0.9, crop=high))
    assert c.best_crop() is high


def test_empty_consensus():
    assert make().best() is None
