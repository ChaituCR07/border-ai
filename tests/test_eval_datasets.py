"""Unit tests for dataset adapters and class mapping schemas."""
import json
import os
import tempfile

from evaluation.datasets.base import Box, DetSample, GtObject
from evaluation.datasets.bdd100k import Bdd100kDetectionDataset
from evaluation.datasets.cctv_custom import CctvCustomDetectionDataset, CctvCustomTrackingSequence
from evaluation.datasets.coco import CocoDetectionDataset
from evaluation.datasets.mot17 import Mot17Dataset, Mot17Sequence


def test_box_geometry_and_foot_point() -> None:
    box = Box(x=10.0, y=20.0, w=30.0, h=40.0)
    assert box.x2 == 40.0
    assert box.y2 == 60.0
    assert box.area == 1200.0
    # Bottom center foot-point
    fx, fy = box.foot_point
    assert fx == 25.0
    assert fy == 60.0
    assert box.to_tlbr() == [10.0, 20.0, 40.0, 60.0]
    assert box.to_tlwh() == [10.0, 20.0, 30.0, 40.0]


def test_coco_adapter_mapping_and_crowd_ignore() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ann_path = os.path.join(tmpdir, "instances.json")
        coco_data = {
            "images": [
                {"id": 101, "file_name": "000101.jpg", "width": 640, "height": 480},
                {"id": 102, "file_name": "000102.jpg", "width": 640, "height": 480},
            ],
            "categories": [
                {"id": 1, "name": "person"},
                {"id": 3, "name": "car"},
                {"id": 99, "name": "couch"},
            ],
            "annotations": [
                {"image_id": 101, "category_id": 1, "bbox": [10, 20, 30, 40], "iscrowd": 0},
                {"image_id": 101, "category_id": 3, "bbox": [50, 60, 70, 80], "iscrowd": 1},
                {"image_id": 101, "category_id": 99, "bbox": [1, 2, 3, 4], "iscrowd": 0},
                {"image_id": 102, "category_id": 1, "bbox": [15, 25, 35, 45], "iscrowd": 0},
            ],
        }
        with open(ann_path, "w", encoding="utf-8") as f:
            json.dump(coco_data, f)

        # Test subset filtering to image 101
        dataset = CocoDetectionDataset(
            annotations_path=ann_path,
            images_dir=tmpdir,
            subset_ids={101},
        )
        assert len(dataset) == 1
        sample = dataset.samples[0]
        assert sample.image_id == "101"
        assert len(sample.gt) == 3

        # Person not crowd -> evaluated
        assert sample.gt[0].cls == "person"
        assert sample.gt[0].ignore is False

        # Car crowd -> ignore
        assert sample.gt[1].cls == "car"
        assert sample.gt[1].ignore is True

        # Couch unmapped -> ignore
        assert sample.gt[2].cls == "couch"
        assert sample.gt[2].ignore is True


def test_bdd100k_adapter_mapping_and_attributes() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ann_path = os.path.join(tmpdir, "bdd_labels.json")
        bdd_data = [
            {
                "name": "clip_001.jpg",
                "attributes": {
                    "weather": "rainy",
                    "timeofday": "night",
                    "scene": "city street",
                },
                "labels": [
                    {
                        "category": "pedestrian",
                        "attributes": {"occluded": True, "truncated": False},
                        "box2d": {"x1": 10.0, "y1": 20.0, "x2": 40.0, "y2": 70.0},
                    },
                    {
                        "category": "rider",
                        "attributes": {"occluded": False, "truncated": False},
                        "box2d": {"x1": 50.0, "y1": 60.0, "x2": 90.0, "y2": 110.0},
                    },
                    {
                        "category": "traffic light",
                        "attributes": {},
                        "box2d": {"x1": 1.0, "y1": 2.0, "x2": 5.0, "y2": 6.0},
                    },
                ],
            }
        ]
        with open(ann_path, "w", encoding="utf-8") as f:
            json.dump(bdd_data, f)

        dataset = Bdd100kDetectionDataset(annotations_path=ann_path, images_dir=tmpdir)
        assert len(dataset) == 1
        sample = dataset.samples[0]
        assert sample.meta["weather"] == "rainy"
        assert sample.meta["timeofday"] == "night"

        # pedestrian -> person
        assert sample.gt[0].cls == "person"
        assert sample.gt[0].ignore is False
        assert sample.gt[0].attrs["occluded"] is True

        # rider -> person
        assert sample.gt[1].cls == "person"
        assert sample.gt[1].ignore is False

        # traffic light -> unmapped, ignored
        assert sample.gt[2].ignore is True


def test_mot17_sequence_parsing_and_static_moving_flag() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        seq_dir = os.path.join(tmpdir, "MOT17-04-FRCNN")
        os.makedirs(os.path.join(seq_dir, "gt"))
        os.makedirs(os.path.join(seq_dir, "img1"))

        # Write seqinfo.ini
        with open(os.path.join(seq_dir, "seqinfo.ini"), "w") as f:
            f.write("[Sequence]\nname=MOT17-04-FRCNN\nframeRate=30\nseqLength=3\nimWidth=1920\nimHeight=1080\nimDir=img1\nimExt=.jpg\n")

        # Write gt.txt: frame, id, x, y, w, h, conf, class_id, visibility
        # MOT17 class 1 = pedestrian; class 7 = static person
        gt_content = (
            "1,1,100,150,50,120,1,1,1.0\n"
            "1,2,300,350,40,100,1,7,0.5\n"
            "2,1,105,152,50,120,1,1,0.9\n"
            "3,1,110,155,50,120,0,1,0.8\n"  # conf 0 -> ignore
        )
        with open(os.path.join(seq_dir, "gt", "gt.txt"), "w") as f:
            f.write(gt_content)

        seq = Mot17Sequence(seq_dir)
        assert seq.name == "MOT17-04-FRCNN"
        assert seq.is_static_camera is True
        assert seq.fps == 30.0
        assert seq.seq_length == 3

        frames = list(seq.frames())
        assert len(frames) == 3

        # Frame 1: 1 active pedestrian, 1 static person ignored
        f1_gt = frames[0].gt
        assert len(f1_gt) == 2
        assert f1_gt[0].cls == "person" and f1_gt[0].ignore is False
        assert f1_gt[1].ignore is True  # class 7

        # Frame 3: conf=0 -> ignored
        f3_gt = frames[2].gt
        assert len(f3_gt) == 1
        assert f3_gt[0].ignore is True


def test_cctv_custom_adapter() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ann_path = os.path.join(tmpdir, "cctv_eval.json")
        cctv_data = {
            "images": [
                {
                    "id": "cam01_0001",
                    "file_name": "cam01_0001.jpg",
                    "camera_id": "cctv_fence_east",
                    "environment": {"time_of_day": "dusk", "weather": "fog"},
                    "annotations": [
                        {"category": "person", "bbox": [100, 200, 50, 100], "track_id": 42}
                    ],
                }
            ]
        }
        with open(ann_path, "w") as f:
            json.dump(cctv_data, f)

        dataset = CctvCustomDetectionDataset(annotations_path=ann_path, images_dir=tmpdir)
        assert len(dataset) == 1
        sample = dataset.samples[0]
        assert sample.meta["camera_id"] == "cctv_fence_east"
        assert sample.meta["time_of_day"] == "dusk"
        assert sample.gt[0].track_id == 42


def test_subsets_existence_and_non_empty() -> None:
    subsets_dir = os.path.join(os.path.dirname(__file__), "..", "evaluation", "datasets", "subsets")
    coco_sub = os.path.join(subsets_dir, "coco_val_1000.txt")
    bdd_dev = os.path.join(subsets_dir, "bdd_val_500_dev.txt")
    bdd_test = os.path.join(subsets_dir, "bdd_val_500_test.txt")
    mot_split = os.path.join(subsets_dir, "mot17_splits.json")

    assert os.path.exists(coco_sub)
    with open(coco_sub) as f:
        coco_ids = [line.strip() for line in f if line.strip()]
    assert len(coco_ids) == 1000

    assert os.path.exists(bdd_dev)
    with open(bdd_dev) as f:
        dev_names = [line.strip() for line in f if line.strip()]
    assert len(dev_names) == 500

    assert os.path.exists(bdd_test)
    with open(bdd_test) as f:
        test_names = [line.strip() for line in f if line.strip()]
    assert len(test_names) == 500

    # Ensure dev and test splits are disjoint
    assert len(set(dev_names).intersection(set(test_names))) == 0

    assert os.path.exists(mot_split)
    with open(mot_split) as f:
        splits = json.load(f)
    assert "train_static" in splits
    assert "val_static" in splits
    assert "dev_tuning" in splits
