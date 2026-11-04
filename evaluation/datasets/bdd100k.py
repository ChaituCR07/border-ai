"""BDD100K detection dataset adapter."""
import json
import os
from typing import Any, Dict, Iterator, List, Optional, Set

from evaluation.datasets.base import Box, DetSample, GtObject


class Bdd100kDetectionDataset:
    """Loads BDD100K format annotations and maps them to the project evaluation schema."""

    def __init__(
        self,
        annotations_path: str,
        images_dir: str,
        class_map: Optional[Dict[str, str]] = None,
        subset_names: Optional[Set[str]] = None,
        name: str = "bdd100k_val",
    ) -> None:
        self.annotations_path = annotations_path
        self.images_dir = images_dir
        self.name = name
        self.subset_names = subset_names

        if class_map is None:
            default_map_path = os.path.join(
                os.path.dirname(__file__), "..", "configs", "class_maps", "bdd_to_project.json"
            )
            if os.path.exists(default_map_path):
                with open(default_map_path, "r", encoding="utf-8") as f:
                    self.class_map = json.load(f)
            else:
                self.class_map = {
                    "pedestrian": "person",
                    "rider": "person",
                    "car": "car",
                    "truck": "truck",
                    "bus": "bus",
                    "motorcycle": "motorcycle",
                    "bicycle": "bicycle",
                }
        else:
            self.class_map = class_map

        self.samples: List[DetSample] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.annotations_path):
            return

        with open(self.annotations_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            file_name = item.get("name", "")
            if self.subset_names is not None and file_name not in self.subset_names:
                continue

            img_path = os.path.join(self.images_dir, file_name)
            img_attrs = item.get("attributes", {})
            gt_objects: List[GtObject] = []

            for label in item.get("labels", []):
                box2d = label.get("box2d")
                if not box2d:
                    continue

                x1 = float(box2d.get("x1", 0))
                y1 = float(box2d.get("y1", 0))
                x2 = float(box2d.get("x2", 0))
                y2 = float(box2d.get("y2", 0))
                w = max(0.0, x2 - x1)
                h = max(0.0, y2 - y1)
                box = Box(x=x1, y=y1, w=w, h=h)

                cat = label.get("category", "")
                target_cls = self.class_map.get(cat)
                label_attrs = label.get("attributes", {})
                is_ignored = target_cls is None

                gt_objects.append(
                    GtObject(
                        cls=target_cls or cat,
                        box=box,
                        ignore=is_ignored,
                        attrs={
                            "occluded": label_attrs.get("occluded", False),
                            "truncated": label_attrs.get("truncated", False),
                            "raw_category": cat,
                        },
                    )
                )

            self.samples.append(
                DetSample(
                    image_id=file_name,
                    path=img_path,
                    width=1280,  # standard BDD100K resolution
                    height=720,
                    gt=gt_objects,
                    meta={
                        "weather": img_attrs.get("weather", "unknown"),
                        "timeofday": img_attrs.get("timeofday", "unknown"),
                        "scene": img_attrs.get("scene", "unknown"),
                    },
                )
            )

    def __iter__(self) -> Iterator[DetSample]:
        return iter(self.samples)

    def __len__(self) -> int:
        return len(self.samples)
