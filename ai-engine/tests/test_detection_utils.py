import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest

from app.detection.classes import resolve_class_ids
from app.pipeline.visualizer import draw_detections, make_grid
from app.schemas.detection import Detection
from app import config
from app.detection.inference import load_model, run_inference


def test_resolve_class_ids():
    names = {0: "person", 2: "car", 7: "truck"}
    assert resolve_class_ids(names, ["person", "car"]) == [0, 2]


def test_resolve_class_ids_missing_raises():
    with pytest.raises(ValueError):
        resolve_class_ids({0: "person"}, ["spaceship"])


def test_detection_geometry():
    d = Detection(0, "person", 0.9, 10, 20, 50, 100)
    assert d.width == 40 and d.height == 80
    assert d.center == (30, 60)
    assert d.bottom_center == (30, 100)


def test_draw_detections_changes_pixels_and_keeps_shape():
    img = np.zeros((360, 640, 3), np.uint8)
    out = draw_detections(img, [Detection(2, "car", 0.8, 100, 100, 300, 250)])
    assert out.shape == (360, 640, 3)
    assert out.any()


def test_draw_label_near_top_edge_does_not_crash():
    img = np.zeros((100, 100, 3), np.uint8)
    draw_detections(img, [Detection(0, "person", 0.5, 0, 0, 50, 50)])


def test_make_grid_pads_missing_tiles():
    tile = np.zeros((360, 640, 3), np.uint8)
    grid = make_grid([tile, tile, tile], cols=2)
    assert grid.shape == (720, 1280, 3)


@pytest.mark.skipif(not (config.MODEL_DIR / "yolov8n.pt").exists(),
                    reason="weights not downloaded")
def test_blank_image_gives_no_detections():
    model = load_model("yolov8n.pt")
    dets, speed = run_inference(model, np.zeros((480, 640, 3), np.uint8),
                                conf=0.4, iou=0.5, imgsz=640)
    assert dets == []
    assert "inference" in speed
