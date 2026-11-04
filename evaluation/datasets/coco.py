"""COCO detection dataset adapter."""
import json
import os
from typing import Any, Dict, Iterator, List, Optional, Set

from evaluation.datasets.base import Box, DetSample, GtObject


class CocoDetectionDataset:
    """Loads COCO format annotations and maps them to the project evaluation schema."""

    def __init__(
        self,
        annotations_path: str,
        images_dir: str,
        class_map: Optional[Dict[str, str]] = None,
        subset_ids: Optional[Set[int]] = None,
        name: str = "coco_val2017",
    ) -> None:
        self.annotations_path = annotations_path
        self.images_dir = images_dir
        self.name = name
        self.subset_ids = subset_ids

        # Load class map if not provided
        if class_map is None:
            default_map_path = os.path.join(
                os.path.dirname(__file__), "..", "configs", "class_maps", "coco_to_project.json"
            )
            if os.path.exists(default_map_path):
                with open(default_map_path, "r", encoding="utf-8") as f:
                    self.class_map = json.load(f)
            else:
                self.class_map = {
                    "person": "person",
                    "bicycle": "bicycle",
                    "car": "car",
                    "motorcycle": "motorcycle",
                    "bus": "bus",
                    "truck": "truck",
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

        cat_id_to_name: Dict[int, str] = {cat["id"]: cat["name"] for cat in data.get("categories", [])}

        # Index annotations by image_id
        img_annotations: Dict[int, List[Dict[str, Any]]] = {}
        for ann in data.get("annotations", []):
            img_id = ann["image_id"]
            if self.subset_ids is not None and img_id not in self.subset_ids:
                continue
            img_annotations.setdefault(img_id, []).append(ann)

        for img in data.get("images", []):
            img_id = img["id"]
            if self.subset_ids is not None and img_id not in self.subset_ids:
                continue

            file_name = img.get("file_name", f"{img_id:012d}.jpg")
            img_path = os.path.join(self.images_dir, file_name)

            gt_objects: List[GtObject] = []
            for ann in img_annotations.get(img_id, []):
                cat_name = cat_id_to_name.get(ann.get("category_id", -1), "")
                target_cls = self.class_map.get(cat_name)
                is_crowd = bool(ann.get("iscrowd", 0))

                bbox = ann.get("bbox", [0, 0, 0, 0])
                box = Box(x=float(bbox[0]), y=float(bbox[1]), w=float(bbox[2]), h=float(bbox[3]))

                if target_cls is None:
                    # Unmapped classes are either ignored if overlapping or skipped
                    gt_objects.append(GtObject(cls=cat_name or "unknown", box=box, ignore=True))
                else:
                    gt_objects.append(
                        GtObject(
                            cls=target_cls,
                            box=box,
                            ignore=is_crowd,
                            attrs={"area": ann.get("area", box.area), "iscrowd": is_crowd},
                        )
                    )

            self.samples.append(
                DetSample(
                    image_id=str(img_id),
                    path=img_path,
                    width=int(img.get("width", 0)),
                    height=int(img.get("height", 0)),
                    gt=gt_objects,
                    meta={"file_name": file_name},
                )
            )

    def __iter__(self) -> Iterator[DetSample]:
        return iter(self.samples)

    def __len__(self) -> int:
        return len(self.samples)
