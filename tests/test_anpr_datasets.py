"""Unit tests for Indian ANPR dataset adapter, QA validation, and split disjointness."""
import json
import os
import tempfile

from evaluation.anpr.datasets.india_anpr import AnprSample, IndiaAnprDataset
from evaluation.datasets.base import Box


def test_anpr_sample_geometry_and_buckets() -> None:
    sample = AnprSample(
        sample_id="s1",
        image_path="/tmp/test.jpg",
        vehicle_id="v_001",
        vehicle_type="car",
        vehicle_bbox=Box(100, 200, 400, 300),
        plate_bbox=Box(200, 400, 120, 45),  # height = 45 px
        plate_text="KA 01 AB 1234",
        plate_norm="KA01AB1234",
        plate_lines=1,
    )
    assert sample.plate_height_px == 45.0
    assert sample.plate_height_bucket == "30-50px"

    # Test edge buckets
    s_small = AnprSample(
        sample_id="s2",
        image_path="/tmp/test2.jpg",
        vehicle_id="v_002",
        vehicle_type="motorcycle",
        vehicle_bbox=Box(10, 10, 50, 50),
        plate_bbox=Box(15, 20, 30, 18),  # height = 18 px
        plate_text="DL01A1234",
        plate_norm="DL01A1234",
    )
    assert s_small.plate_height_bucket == "<20px"

    s_large = AnprSample(
        sample_id="s3",
        image_path="/tmp/test3.jpg",
        vehicle_id="v_003",
        vehicle_type="truck",
        vehicle_bbox=Box(10, 10, 500, 500),
        plate_bbox=Box(15, 20, 200, 85),  # height = 85 px
        plate_text="MH12DE1433",
        plate_norm="MH12DE1433",
    )
    assert s_large.plate_height_bucket == ">80px"


def test_india_anpr_dataset_loading_and_subset_filter() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ann_path = os.path.join(tmpdir, "anpr_data.json")
        data = {
            "samples": [
                {
                    "id": "sample_101",
                    "vehicle_id": "v_010",
                    "file_name": "sample_101.jpg",
                    "vehicle_type": "car",
                    "vehicle_bbox": [50, 50, 200, 150],
                    "plate_bbox": [80, 120, 80, 25],
                    "plate_text": "KA-01-AB-1234",
                    "unreadable": False,
                },
                {
                    "id": "sample_102",
                    "vehicle_id": "v_020",
                    "file_name": "sample_102.jpg",
                    "vehicle_type": "motorcycle",
                    "vehicle_bbox": [20, 20, 100, 100],
                    "plate_bbox": [30, 60, 40, 35],
                    "plate_text": "",
                    "unreadable": True,
                },
            ]
        }
        with open(ann_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Full dataset
        ds_all = IndiaAnprDataset(annotations_path=ann_path, images_dir=tmpdir)
        assert len(ds_all) == 2
        assert ds_all.vehicles == {"v_010", "v_020"}

        s1 = ds_all.samples[0]
        assert s1.sample_id == "sample_101"
        assert s1.plate_norm == "KA01AB1234"
        assert s1.unreadable is False

        s2 = ds_all.samples[1]
        assert s2.unreadable is True
        assert s2.plate_height_bucket == "30-50px"

        # Vehicle subset filter
        ds_filtered = IndiaAnprDataset(
            annotations_path=ann_path,
            images_dir=tmpdir,
            vehicle_subset={"v_010"},
        )
        assert len(ds_filtered) == 1
        assert ds_filtered.samples[0].vehicle_id == "v_010"


def test_vehicle_splits_disjointness_and_counts() -> None:
    splits_dir = os.path.join(
        os.path.dirname(__file__), "..", "evaluation", "anpr", "datasets", "splits"
    )
    dev_path = os.path.join(splits_dir, "india_anpr_dev_vehicles.txt")
    test_path = os.path.join(splits_dir, "india_anpr_test_vehicles.txt")

    assert os.path.exists(dev_path), f"Missing {dev_path}"
    assert os.path.exists(test_path), f"Missing {test_path}"

    with open(dev_path, "r", encoding="utf-8") as f:
        dev_ids = [line.strip() for line in f if line.strip()]

    with open(test_path, "r", encoding="utf-8") as f:
        test_ids = [line.strip() for line in f if line.strip()]

    assert len(dev_ids) == 80
    assert len(test_ids) == 120

    # Ensure strict disjointness between dev and test vehicle sets
    overlap = set(dev_ids).intersection(set(test_ids))
    assert len(overlap) == 0, f"Detected vehicle split leakage: {overlap}"
