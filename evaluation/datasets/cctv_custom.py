"""Custom CCTV and border surveillance dataset adapter."""
import json
import os
from typing import Any, Dict, Iterator, List, Optional

from evaluation.datasets.base import Box, DetSample, GtObject, TrackingFrame, TrackingSequence


class CctvCustomDetectionDataset:
    """Loads CCTV border benchmark frames for detection evaluation."""

    def __init__(self, annotations_path: str, images_dir: str, name: str = "cctv_border_eval") -> None:
        self.annotations_path = annotations_path
        self.images_dir = images_dir
        self.name = name
        self.samples: List[DetSample] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.annotations_path):
            return

        with open(self.annotations_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("images", []):
            img_id = str(item.get("id", item.get("file_name", "")))
            file_name = item.get("file_name", "")
            img_path = os.path.join(self.images_dir, file_name)
            width = int(item.get("width", 1920))
            height = int(item.get("height", 1080))
            camera_id = item.get("camera_id", "cam_01")
            environment = item.get("environment", {})

            gt_objects: List[GtObject] = []
            for ann in item.get("annotations", []):
                cls_name = ann.get("category", ann.get("cls", "person"))
                bbox = ann.get("bbox", [0, 0, 0, 0])
                box = Box(x=float(bbox[0]), y=float(bbox[1]), w=float(bbox[2]), h=float(bbox[3]))
                gt_objects.append(
                    GtObject(
                        cls=cls_name,
                        box=box,
                        track_id=ann.get("track_id"),
                        ignore=bool(ann.get("ignore", False)),
                        attrs=ann.get("attributes", {}),
                    )
                )

            self.samples.append(
                DetSample(
                    image_id=img_id,
                    path=img_path,
                    width=width,
                    height=height,
                    gt=gt_objects,
                    meta={
                        "camera_id": camera_id,
                        "time_of_day": environment.get("time_of_day", "day"),
                        "weather": environment.get("weather", "clear"),
                        "is_infrared": environment.get("infrared", False),
                    },
                )
            )

    def __iter__(self) -> Iterator[DetSample]:
        return iter(self.samples)

    def __len__(self) -> int:
        return len(self.samples)


class CctvCustomTrackingSequence(TrackingSequence):
    """Loads a CCTV surveillance video clip as a TrackingSequence."""

    def __init__(self, sequence_data: Dict[str, Any], images_dir: str) -> None:
        self.seq_name = sequence_data.get("sequence_id", "cctv_seq")
        self.fps = float(sequence_data.get("fps", 25.0))
        self.width = int(sequence_data.get("width", 1920))
        self.height = int(sequence_data.get("height", 1080))
        self.is_static_camera = True
        self.images_dir = images_dir
        self._frames: List[TrackingFrame] = []

        for frame_dict in sequence_data.get("frames", []):
            frame_idx = int(frame_dict["frame_index"])
            file_name = frame_dict.get("file_name", f"{frame_idx:06d}.jpg")
            img_path = os.path.join(images_dir, file_name)
            timestamp = float(frame_dict.get("timestamp", (frame_idx - 1) / self.fps))

            gt_objs: List[GtObject] = []
            for ann in frame_dict.get("annotations", []):
                bbox = ann.get("bbox", [0, 0, 0, 0])
                box = Box(x=float(bbox[0]), y=float(bbox[1]), w=float(bbox[2]), h=float(bbox[3]))
                gt_objs.append(
                    GtObject(
                        cls=ann.get("category", "person"),
                        box=box,
                        track_id=ann.get("track_id"),
                        ignore=bool(ann.get("ignore", False)),
                        attrs=ann.get("attributes", {}),
                    )
                )

            self._frames.append(
                TrackingFrame(
                    frame_index=frame_idx,
                    timestamp=timestamp,
                    image_path=img_path,
                    gt=gt_objs,
                )
            )

    @property
    def name(self) -> str:
        return self.seq_name

    def frames(self) -> Iterator[TrackingFrame]:
        return iter(self._frames)

    def __len__(self) -> int:
        return len(self._frames)
