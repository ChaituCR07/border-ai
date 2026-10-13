import pytest
import numpy as np

from app.anpr.plate_format import (
    PlateFormats,
    clean_text,
    correct_indian,
    INDIAN_STATE_CODES,
    LAYOUTS
)
from app.anpr.consensus import PlateConsensus
from app.anpr.types import PlateRead
from app.anpr.preprocess import (
    crop_with_pad,
    plate_quality,
    preprocess
)
from app.anpr.config import QualityConfig
from app.anpr.types import PlateBox


# ----------------------------------------------------------------------
# 1. Exhaustive State Code & Layout Tests
# ----------------------------------------------------------------------

def test_all_official_state_codes():
    f = PlateFormats(["indian"])
    for state in sorted(INDIAN_STATE_CODES):
        plate = f"{state}01AB1234"
        check = f.check(plate)
        assert check.level == "strict", f"State {state} should be strict, got {check.level}"
        assert check.text == plate


def test_all_indian_layouts():
    f = PlateFormats(["indian"])
    # Layouts: (district digits, series letters)
    # (2, 2) -> KA01AB1234
    # (2, 1) -> KA01A1234
    # (2, 3) -> KA01ABC1234
    # (1, 2) -> KA1AB1234
    # (1, 1) -> KA1A1234
    # (1, 3) -> KA1ABC1234
    samples = [
        ("KA01AB1234", (2, 2)),
        ("MH12A5678", (2, 1)),
        ("DL04XYZ9999", (2, 3)),
        ("TN9AB4321", (1, 2)),
        ("UP5Z1111", (1, 1)),
        ("GJ3ABC8888", (1, 3)),
    ]
    for text, (d, s) in samples:
        check = f.check(text)
        assert check.level == "strict"
        assert check.text == text


def test_exhaustive_lookalike_character_corrections():
    # Test each substitution rule:
    # Digits in letter positions:
    # 0 -> O, 1 -> I, 2 -> Z, 4 -> A, 5 -> S, 6 -> G, 7 -> T, 8 -> B
    cases = [
        ("KA014B1234", "KA01AB1234"),  # 4 in series -> A
        ("KA018B1234", "KA01BB1234"),  # 8 in series -> B
        ("KA015B1234", "KA01SB1234"),  # 5 in series -> S
        ("KA012B1234", "KA01ZB1234"),  # 2 in series -> Z
        ("KA017B1234", "KA01TB1234"),  # 7 in series -> T
        ("KA016B1234", "KA01GB1234"),  # 6 in series -> G
        # Letters in digit positions:
        # O -> 0, I -> 1, Z -> 2, A -> 4, S -> 5, G -> 6, T -> 7, B -> 8
        ("KAOIAB1234", "KA01AB1234"),  # O -> 0, I -> 1 in district
        ("KA01ABIZ34", "KA01AB1234"),  # I -> 1, Z -> 2 in registration
        ("KA01ABASTB", "KA01AB4578"),  # A->4, S->5, T->7, B->8 in registration
    ]
    for noisy, expected in cases:
        cand = correct_indian(noisy)
        assert cand is not None, f"Failed to correct {noisy}"
        assert cand.text == expected, f"Expected {expected} for {noisy}, got {cand.text}"


def test_noisy_prefixes_and_suffixes():
    f = PlateFormats(["indian"])
    # Common OCR artifacts: "IND", "GOVT", "POLICE", border dashes
    assert f.check("IND.KA-01-AB-1234").text == "KA01AB1234"
    assert f.check("POLICE KA 01 AB 1234").text == "KA01AB1234"
    assert f.check("---KA01AB1234***").text == "KA01AB1234"
    assert f.check("ka 01 ab 1234").text == "KA01AB1234"


def test_international_and_generic_formats():
    f = PlateFormats(["indian", "generic"])
    # European / US style plates (no Indian state code)
    assert f.check("B-MW-1234").level == "loose"
    assert f.check("7XYZ890").level == "loose"
    assert f.check("ABCDE").level == "loose"  # min 5 chars
    assert f.check("ABC1234567").level == "loose"  # max 10 chars
    # Below min or above max length
    assert f.check("A").level == "invalid"
    assert f.check("ABCD").level == "invalid"
    assert f.check("TOOLONGFORTHEFORMAT12345").level == "invalid"


# ----------------------------------------------------------------------
# 2. Advanced Consensus Voting Edge Cases
# ----------------------------------------------------------------------

def test_consensus_tie_breaker():
    # Two candidates with equal votes
    c = PlateConsensus(lambda t: (t, "strict"), min_reads=3, stable_share=0.5)
    c.add(PlateRead("KA01AB1234", "KA01AB1234", 0.9, 0.9, 1.0, "strict", 0, 0.0))
    c.add(PlateRead("KA01AB1284", "KA01AB1284", 0.8, 0.8, 1.0, "strict", 1, 0.1))
    best = c.best()
    assert best is not None
    # Weighted by confidence, 0.9 wins over 0.8
    assert best.text == "KA01AB1234"


def test_character_vote_across_multi_error_reads():
    # 4 readings with different character slips
    c = PlateConsensus(lambda t: (t, "strict"), min_reads=3, stable_share=0.5)
    # True plate is KA01AB1234
    c.add(PlateRead("KA01AB1239", "KA01AB1239", 0.8, 0.8, 1.0, "strict", 0, 0.0))  # 4 -> 9
    c.add(PlateRead("KA01AB1284", "KA01AB1284", 0.8, 0.8, 1.0, "strict", 1, 0.1))  # 3 -> 8
    c.add(PlateRead("KA01AB1634", "KA01AB1634", 0.8, 0.8, 1.0, "strict", 2, 0.2))  # 2 -> 6
    c.add(PlateRead("KA01A81234", "KA01A81234", 0.8, 0.8, 1.0, "strict", 3, 0.3))  # B -> 8
    best = c.best()
    assert best is not None
    assert best.text == "KA01AB1234"
    assert best.method == "char"


def test_consensus_format_level_preference():
    # A strict Indian format read should take precedence over a generic invalid read
    c = PlateConsensus(lambda t: (t, "strict" if t.startswith("KA") else "loose"), min_reads=2, stable_share=0.5)
    c.add(PlateRead("KA01AB1234", "KA01AB1234", 0.7, 0.7, 1.0, "strict", 0, 0.0))
    c.add(PlateRead("KA01AB1234", "KA01AB1234", 0.7, 0.7, 1.0, "strict", 1, 0.1))
    c.add(PlateRead("SOMEJUNK", "SOMEJUNK", 0.8, 0.8 * 0.6, 1.0, "loose", 2, 0.2))
    best = c.best()
    assert best.text == "KA01AB1234"
    assert c.is_stable(best)


# ----------------------------------------------------------------------
# 3. Preprocessing & Quality Gate Boundary Conditions
# ----------------------------------------------------------------------

def test_extreme_blank_and_noise_images():
    q = QualityConfig(min_sharpness=40.0)
    # Pure black image
    black = np.zeros((60, 160, 3), np.uint8)
    q_black = plate_quality(black, q)
    assert not q_black.ok
    assert q_black.sharpness == 0.0

    # Pure white image
    white = np.full((60, 160, 3), 255, np.uint8)
    q_white = plate_quality(white, q)
    assert not q_white.ok

    # Salt-and-pepper high frequency noise should have high sharpness
    noise = np.random.default_rng(42).integers(0, 255, (60, 160, 3), dtype=np.uint8)
    q_noise = plate_quality(noise, q)
    assert q_noise.ok
    assert q_noise.sharpness > 40.0


def test_extreme_aspect_ratio_crops():
    img = np.zeros((100, 200, 3), np.uint8)
    # Very thin vertical box
    vert_box = PlateBox(10, 10, 15, 90, 0.9)
    crop_vert = crop_with_pad(img, vert_box, pad=0.1)
    assert crop_vert.shape[0] > 0 and crop_vert.shape[1] > 0

    # Very wide horizontal box
    horiz_box = PlateBox(10, 40, 190, 50, 0.9)
    crop_horiz = crop_with_pad(img, horiz_box, pad=0.1)
    assert crop_horiz.shape[0] > 0 and crop_horiz.shape[1] > 0


def test_quality_gate_threshold_boundaries():
    q = QualityConfig(min_plate_width_px=50, min_plate_height_px=15, min_sharpness=40.0)
    img_49_15 = np.random.default_rng(0).integers(0, 255, (15, 49, 3), dtype=np.uint8)
    assert plate_quality(img_49_15, q).reason == "too_small"

    img_50_14 = np.random.default_rng(0).integers(0, 255, (14, 50, 3), dtype=np.uint8)
    assert plate_quality(img_50_14, q).reason == "too_short"
