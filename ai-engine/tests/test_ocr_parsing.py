import numpy as np

from app.anpr.ocr import assemble, parse_v2_result, parse_v3_result


def box(x1, y1, x2, y2):
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def test_v2_two_line_plate_is_read_top_to_bottom():
    raw = [[[box(0, 40, 100, 70), ("AB1234", 0.8)],       # listed second line first on purpose
            [box(0, 0, 100, 30), ("KA01", 0.9)]]]
    r = assemble(parse_v2_result(raw))
    assert r.text == "KA01AB1234"
    assert abs(r.confidence - (0.9 * 4 + 0.8 * 6) / 10) < 1e-9


def test_v2_nothing_found():
    assert assemble(parse_v2_result([None])).text == ""
    assert assemble(parse_v2_result(None)).text == ""


def test_v3_dict_result_with_polygons():
    res = {"rec_texts": ["AB1234", "KA01"], "rec_scores": [0.8, 0.9],
           "rec_polys": [np.array(box(0, 40, 100, 70)), np.array(box(0, 0, 100, 30))]}
    assert assemble(parse_v3_result(res)).text == "KA01AB1234"


def test_v3_result_with_xyxy_boxes():
    res = {"rec_texts": ["1234", "KA01AB"], "rec_scores": [0.7, 0.9],
           "rec_boxes": np.array([[200, 0, 300, 30], [0, 0, 190, 30]])}
    assert assemble(parse_v3_result(res)).text == "KA01AB1234"          # same line: left to right


def test_texts_without_boxes_keep_their_order():
    res = {"rec_texts": ["KA01", "AB1234"], "rec_scores": [0.9, 0.9]}
    assert assemble(parse_v3_result(res)).text == "KA01AB1234"
