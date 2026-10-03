from typing import List, Optional, Tuple

import cv2
import numpy as np

from app.schemas.detection import Detection

FONT = cv2.FONT_HERSHEY_SIMPLEX

# BGR colors per class; anything else gets a stable fallback color
CLASS_COLORS = {
    "person": (0, 200, 0),
    "bicycle": (255, 200, 0),
    "car": (255, 128, 0),
    "motorcycle": (200, 0, 200),
    "bus": (0, 165, 255),
    "truck": (0, 0, 255),
}


def color_for(class_name: str) -> Tuple[int, int, int]:
    if class_name in CLASS_COLORS:
        return CLASS_COLORS[class_name]
    h = abs(hash(class_name))
    return (h % 200 + 55, (h // 7) % 200 + 55, (h // 49) % 200 + 55)


def put_text(img, text: str, org, scale: float = 0.55, color=(0, 255, 0)) -> None:
    """Readable text on any background (dark outline + colored fill)."""
    cv2.putText(img, text, org, FONT, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, FONT, scale, color, 1, cv2.LINE_AA)


def draw_detections(image: np.ndarray, detections: List[Detection],
                    show_conf: bool = True) -> np.ndarray:
    """Draw boxes and labels in place and return the image."""
    h, w = image.shape[:2]
    thickness = max(1, round(min(h, w) / 400))      # scale with resolution
    font_scale = max(0.4, min(h, w) / 1000)

    for d in detections:
        color = color_for(d.class_name)
        p1, p2 = (int(d.x1), int(d.y1)), (int(d.x2), int(d.y2))
        cv2.rectangle(image, p1, p2, color, thickness)

        label = f"{d.class_name} {d.confidence:.2f}" if show_conf else d.class_name
        (tw, th), base = cv2.getTextSize(label, FONT, font_scale, 1)
        y_top = max(p1[1] - th - base, 0)             # keep the label inside the image
        cv2.rectangle(image, (p1[0], y_top), (p1[0] + tw, y_top + th + base), color, -1)
        cv2.putText(image, label, (p1[0], y_top + th), FONT, font_scale,
                    (0, 0, 0), 1, cv2.LINE_AA)
    return image


def make_grid(tiles: List[Optional[np.ndarray]], cols: int = 2,
              tile_size: Tuple[int, int] = (640, 360)) -> np.ndarray:
    """Arrange tiles into a grid. None tiles render as black."""
    w, h = tile_size
    tiles = [t if t is not None else np.zeros((h, w, 3), np.uint8) for t in tiles]
    while len(tiles) % cols:
        tiles.append(np.zeros((h, w, 3), np.uint8))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    return np.vstack(rows)
