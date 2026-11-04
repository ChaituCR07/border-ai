"""MOT17 tracking dataset adapter."""
import configparser
import os
from typing import Dict, Iterator, List, Optional

from evaluation.datasets.base import Box, GtObject, TrackingFrame, TrackingSequence

STATIC_SEQUENCES = {"MOT17-02", "MOT17-04", "MOT17-09"}


class Mot17Sequence(TrackingSequence):
    """Loads a single MOT17 sequence from directory."""

    def __init__(self, seq_dir: str) -> None:
        self.seq_dir = seq_dir
        self.seq_name = os.path.basename(os.path.normpath(seq_dir))
        # Remove detector tag if present (e.g. MOT17-02-FRCNN -> MOT17-02)
        base_name = self.seq_name.split("-")[0] + "-" + self.seq_name.split("-")[1] if "-" in self.seq_name else self.seq_name
        self.is_static_camera = base_name in STATIC_SEQUENCES

        self.ini_path = os.path.join(seq_dir, "seqinfo.ini")
        self.fps = 30.0
        self.width = 1920
        self.height = 1080
        self.seq_length = 0
        self.im_dir = "img1"
        self.im_ext = ".jpg"
        self._load_ini()

        self._frames: Dict[int, List[GtObject]] = {}
        self._load_gt()

    @property
    def name(self) -> str:
        return self.seq_name

    def _load_ini(self) -> None:
        if not os.path.exists(self.ini_path):
            return
        config = configparser.ConfigParser()
        config.read(self.ini_path)
        if "Sequence" in config:
            sec = config["Sequence"]
            self.fps = float(sec.get("frameRate", 30.0))
            self.width = int(sec.get("imWidth", 1920))
            self.height = int(sec.get("imHeight", 1080))
            self.seq_length = int(sec.get("seqLength", 0))
            self.im_dir = sec.get("imDir", "img1")
            self.im_ext = sec.get("imExt", ".jpg")

    def _load_gt(self) -> None:
        gt_path = os.path.join(self.seq_dir, "gt", "gt.txt")
        if not os.path.exists(gt_path):
            return

        with open(gt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 7:
                    continue

                frame_idx = int(parts[0])
                track_id = int(parts[1])
                x = float(parts[2])
                y = float(parts[3])
                w = float(parts[4])
                h = float(parts[5])
                conf = float(parts[6])  # 0 indicates consider as ignore
                class_id = int(parts[7]) if len(parts) > 7 else 1
                vis = float(parts[8]) if len(parts) > 8 else 1.0

                # MOT17: class 1 is pedestrian. Other classes (2, 7, 8, 12) or conf==0 are ignored.
                is_pedestrian = (class_id == 1)
                is_ignored = (not is_pedestrian) or (conf == 0.0)

                gt_obj = GtObject(
                    cls="person",
                    box=Box(x=x, y=y, w=w, h=h),
                    track_id=track_id,
                    ignore=is_ignored,
                    attrs={"visibility": vis, "class_id": class_id, "conf": conf},
                )
                self._frames.setdefault(frame_idx, []).append(gt_obj)

        if not self.seq_length and self._frames:
            self.seq_length = max(self._frames.keys())

    def frames(self) -> Iterator[TrackingFrame]:
        img_folder = os.path.join(self.seq_dir, self.im_dir)
        for frame_idx in range(1, self.seq_length + 1):
            file_name = f"{frame_idx:06d}{self.im_ext}"
            img_path = os.path.join(img_folder, file_name)
            timestamp = (frame_idx - 1) / self.fps
            gt = self._frames.get(frame_idx, [])
            yield TrackingFrame(
                frame_index=frame_idx,
                timestamp=timestamp,
                image_path=img_path,
                gt=gt,
            )

    def __len__(self) -> int:
        return self.seq_length


class Mot17Dataset:
    """Collection of MOT17 sequences."""

    def __init__(self, root_dir: str, sequence_filter: Optional[List[str]] = None) -> None:
        self.root_dir = root_dir
        self.name = "mot17"
        self._sequences: List[Mot17Sequence] = []

        if os.path.exists(root_dir):
            for entry in sorted(os.listdir(root_dir)):
                entry_path = os.path.join(root_dir, entry)
                if os.path.isdir(entry_path):
                    if sequence_filter and entry not in sequence_filter:
                        continue
                    if os.path.exists(os.path.join(entry_path, "seqinfo.ini")):
                        self._sequences.append(Mot17Sequence(entry_path))

    def sequences(self) -> Iterator[Mot17Sequence]:
        return iter(self._sequences)

    def __len__(self) -> int:
        return len(self._sequences)
