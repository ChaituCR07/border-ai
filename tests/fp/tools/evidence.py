"""Evidence package extractor and plate privacy protection.

Ensures:
- Local packaging of false-positive diagnostic frames and metadata.
- Automated blurring/pixelation of vehicle license plates for privacy compliance.
- Refusal to write evidence packages inside tracked source directories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def blur_plate_region(
    pixels: List[List[List[int]]],
    bbox_xyxy: Tuple[int, int, int, int],
    block_size: int = 8,
) -> List[List[List[int]]]:
    """Applies pixelation blurring to a bounding box region in an RGB pixel buffer.

    Args:
        pixels: H x W x 3 nested list of RGB values [0..255].
        bbox_xyxy: (x1, y1, x2, y2) pixel coordinates.
        block_size: Pixelation block size.

    Returns:
        New blurred pixel buffer.
    """
    h = len(pixels)
    if h == 0:
        return []
    w = len(pixels[0])

    # Deep copy buffer
    out = [[[p for p in channel] for channel in row] for row in pixels]

    x1, y1, x2, y2 = bbox_xyxy
    x1 = max(0, min(x1, w - 1))
    x2 = max(0, min(x2, w - 1))
    y1 = max(0, min(y1, h - 1))
    y2 = max(0, min(y2, h - 1))

    if x2 <= x1 or y2 <= y1:
        return out

    for by in range(y1, y2 + 1, block_size):
        for bx in range(x1, x2 + 1, block_size):
            ey = min(by + block_size, y2 + 1)
            ex = min(bx + block_size, x2 + 1)

            # Compute block average
            total_r, total_g, total_b = 0, 0, 0
            count = 0
            for py in range(by, ey):
                for px in range(bx, ex):
                    total_r += pixels[py][px][0]
                    total_g += pixels[py][px][1]
                    total_b += pixels[py][px][2]
                    count += 1

            if count > 0:
                avg_r = total_r // count
                avg_g = total_g // count
                avg_b = total_b // count

                for py in range(by, ey):
                    for px in range(bx, ex):
                        out[py][px][0] = avg_r
                        out[py][px][1] = avg_g
                        out[py][px][2] = avg_b

    return out


def create_evidence_package(
    fp_id: str,
    output_dir: str | Path,
    metadata: Dict[str, Any],
    config_hash: str,
) -> Path:
    """Creates a local evidence folder with sanitized metadata and diagnostic data."""
    out_path = Path(output_dir) / fp_id

    # Refuse writing to source or tracking directories
    resolved = str(out_path.resolve())
    for forbidden in ["/tests/fp/logic", "/engine", "/backend/src", "/frontend/src"]:
        if forbidden in resolved:
            raise ValueError(f"Refusing to write evidence package inside source directory: {resolved}")

    out_path.mkdir(parents=True, exist_ok=True)

    package_meta = {
        "fp_id": fp_id,
        "config_hash": config_hash,
        "payload": metadata,
    }

    meta_file = out_path / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(package_meta, f, indent=2)

    return out_path
