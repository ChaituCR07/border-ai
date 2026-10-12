import cv2
import numpy as np
import pytest

from app.anpr.config import LocatorConfig, QualityConfig
from app.anpr.locator import LowerRegionLocator, filter_boxes
from app.anpr.preprocess import crop_with_pad, plate_quality, preprocess
from app.anpr.types import PlateBox


def noise(h=40, w=120):
    return np.random.default_rng(0).integers(0, 255, (h, w, 3)).astype(np.uint8)


def test_sharp_crop_passes_and_blurred_crop_fails():
    q = QualityConfig()
    assert plate_quality(noise(), q).ok
    blurred = cv2.GaussianBlur(noise(), (31, 31), 0)
    r = plate_quality(blurred, q)
    assert not r.ok and r.reason == "blurry"


def test_small_crop_is_rejected():
    assert plate_quality(noise(10, 30), QualityConfig()).reason in ("too_small", "too_short")


def test_crop_with_pad_is_clamped_to_the_image():
    img = np.zeros((100, 200, 3), np.uint8)
    out = crop_with_pad(img, PlateBox(-20, -20, 40, 30, 0.9), pad=0.5)
    assert out.shape[0] <= 100 and out.shape[1] <= 200 and out.size > 0


def test_preprocess_resizes_and_returns_bgr():
    out = preprocess(noise(40, 120), "clahe", target_h=96, border=8)
    assert out.shape == (96 + 16, 288 + 16, 3)


def test_preprocess_rejects_unknown_mode():
    with pytest.raises(ValueError):
        preprocess(noise(), "magic")


def test_filter_boxes_by_aspect_and_area():
    lc, shape = LocatorConfig(), (200, 400, 3)
    good = PlateBox(100, 120, 200, 150, 0.9)         # 100 x 30: plate-like
    tall = PlateBox(10, 10, 40, 100, 0.95)           # aspect 0.33
    tiny = PlateBox(0, 0, 4, 2, 0.99)                # almost no area
    huge = PlateBox(0, 0, 400, 200, 0.99)            # the whole crop
    assert filter_boxes([tall, tiny, huge, good], shape, lc) == [good]


def test_lower_region_locator_returns_the_bottom_half():
    box = LowerRegionLocator().locate(np.zeros((100, 200, 3), np.uint8))[0]
    assert (box.y1, box.y2, box.x1, box.x2) == (50.0, 100.0, 0.0, 200.0)
