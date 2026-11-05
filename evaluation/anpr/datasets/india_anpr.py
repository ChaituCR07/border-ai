"""BorderVision-India-ANPR dataset adapter and sample validation."""
from dataclasses import dataclass, field
import json
import os
from typing import Any, Dict, Iterator, List, Optional, Set

from evaluation.anpr.metrics import plate_norm
from evaluation.datasets.base import Box


@dataclass
class AnprSample:
    sample_id: str
    image_path: str
    vehicle_id: str
    vehicle_type: str
    vehicle_bbox: Box
    plate_bbox: Box
    plate_text: str
    plate_norm: str
    plate_lines: int = 1
    unreadable: bool = False
    condition: Dict[str, Any] = field(default_factory=dict)

    @property
    def plate_height_px(self) -> float:
        return self.plate_bbox.h

    @property
    def plate_height_bucket(self) -> str:
        """Classifies plate pixel height into practical operational buckets."""
        h = self.plate_bbox.h
        if h < 20.0:
            return "<20px"
        elif h <= 30.0:
            return "20-30px"
        elif h <= 50.0:
            return "30-50px"
        elif h <= 80.0:
            return "50-80px"
        return ">80px"


class IndiaAnprDataset:
    """Loads and validates Indian ANPR dataset samples with vehicle-level grouping."""

    def __init__(
        self,
        annotations_path: str,
        images_dir: str,
        vehicle_subset: Optional[Set[str]] = None,
        name: str = "india_anpr",
    ) -> None:
        self.annotations_path = annotations_path
        self.images_dir = images_dir
        self.vehicle_subset = vehicle_subset
        self.name = name
        self.samples: List[AnprSample] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.annotations_path):
            return

        with open(self.annotations_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            raw_items = data.get("samples", [])
        elif isinstance(data, list):
            raw_items = data
        else:
            raw_items = []

        for item in raw_items:
            v_id = str(item.get("vehicle_id", item.get("session_id", "v_unknown")))
            if self.vehicle_subset is not None and v_id not in self.vehicle_subset:
                continue

            sample_id = str(item.get("id", item.get("sample_id", "")))
            file_name = item.get("file_name", f"{sample_id}.jpg")
            img_path = os.path.join(self.images_dir, file_name)

            v_box_raw = item.get("vehicle_bbox", [0, 0, 100, 100])
            p_box_raw = item.get("plate_bbox", [10, 10, 50, 20])

            v_box = Box(x=float(v_box_raw[0]), y=float(v_box_raw[1]), w=float(v_box_raw[2]), h=float(v_box_raw[3]))
            p_box = Box(x=float(p_box_raw[0]), y=float(p_box_raw[1]), w=float(p_box_raw[2]), h=float(p_box_raw[3]))

            raw_text = str(item.get("plate_text", ""))
            norm_text = plate_norm(raw_text)
            unreadable = bool(item.get("unreadable", False))

            sample = AnprSample(
                sample_id=sample_id,
                image_path=img_path,
                vehicle_id=v_id,
                vehicle_type=item.get("vehicle_type", "car"),
                vehicle_bbox=v_box,
                plate_bbox=p_box,
                plate_text=raw_text,
                plate_norm=norm_text,
                plate_lines=int(item.get("plate_lines", 1)),
                unreadable=unreadable,
                condition=item.get("condition", {
                    "time_of_day": item.get("time_of_day", "day"),
                    "weather": item.get("weather", "clear"),
                    "angle": item.get("angle", "frontal"),
                    "blur": item.get("blur", "none"),
                }),
            )
            self.samples.append(sample)

    def __iter__(self) -> Iterator[AnprSample]:
        return iter(self.samples)

    def __len__(self) -> int:
        return len(self.samples)

    @property
    def vehicles(self) -> Set[str]:
        return {s.vehicle_id for s in self.samples}
