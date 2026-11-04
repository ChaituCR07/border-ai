"""MOT Challenge format I/O utilities (1-based frame indexing)."""
from dataclasses import dataclass
from typing import Dict, Iterator, List, TextIO

from evaluation.datasets.base import Box


@dataclass
class MotRow:
    frame: int  # 1-based index
    track_id: int
    box: Box
    conf: float = 1.0
    x: float = -1.0
    y: float = -1.0
    z: float = -1.0


def read_mot_file(file_path: str) -> Dict[int, List[MotRow]]:
    """Reads MOT format CSV file and returns rows grouped by 1-based frame number."""
    frames: Dict[int, List[MotRow]] = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 6:
                continue

            frame_idx = int(parts[0])
            track_id = int(parts[1])
            x = float(parts[2])
            y = float(parts[3])
            w = float(parts[4])
            h = float(parts[5])
            conf = float(parts[6]) if len(parts) > 6 else 1.0

            row = MotRow(
                frame=frame_idx,
                track_id=track_id,
                box=Box(x=x, y=y, w=w, h=h),
                conf=conf,
            )
            frames.setdefault(frame_idx, []).append(row)
    return frames


def write_mot_file(file_path: str, rows_by_frame: Dict[int, List[MotRow]]) -> None:
    """Writes tracker predictions to a standard MOT challenge format file."""
    with open(file_path, "w", encoding="utf-8") as f:
        for frame_idx in sorted(rows_by_frame.keys()):
            for row in rows_by_frame[frame_idx]:
                f.write(
                    f"{row.frame},{row.track_id},{row.box.x:.2f},{row.box.y:.2f},"
                    f"{row.box.w:.2f},{row.box.h:.2f},{row.conf:.2f},-1,-1,-1\n"
                )
