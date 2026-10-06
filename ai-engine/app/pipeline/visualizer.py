import colorsys
import math
from typing import List, Optional, Tuple

import cv2
import numpy as np

from app.analytics.rules_config import CameraRules
from app.schemas.detection import Detection
from app.schemas.tracking import TrackedObject

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

ZONE_COLORS = {"restricted": (0, 0, 255), "monitored": (0, 200, 255)}   # BGR
FLASH_COLOR = (255, 0, 255)


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


def color_for_id(track_id: int) -> Tuple[int, int, int]:
    """Stable, well-separated color per ID (golden-ratio hue stepping). Returns BGR."""
    hue = (track_id * 0.61803398875) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
    return (int(b * 255), int(g * 255), int(r * 255))


def _draw_trail(image: np.ndarray, trail, color, thickness: int) -> None:
    pts = [(int(x), int(y)) for _, x, y in trail]
    n = len(pts)
    for i in range(1, n):
        frac = i / n                                       # older segments are thinner
        th = max(1, int(thickness * (0.5 + frac)))
        cv2.line(image, pts[i - 1], pts[i], color, th, cv2.LINE_AA)


def draw_tracks(image: np.ndarray, tracks: List[TrackedObject], store=None,
                show_trails: bool = True, show_lost: bool = True) -> np.ndarray:
    """Boxes + 'class #id' labels + trajectory trails. Draws in place."""
    h, w = image.shape[:2]
    thickness = max(1, round(min(h, w) / 400))
    font_scale = max(0.4, min(h, w) / 1000)

    # Ghost trails for lost tracks: handy when debugging ID switches
    if store is not None and show_lost:
        for t in store.lost_tracks():
            if len(t.trail) > 1:
                _draw_trail(image, t.trail, (150, 150, 150), thickness)
                lx, ly = t.last_point
                put_text(image, f"lost #{t.track_id}", (int(lx) + 4, int(ly)),
                         scale=font_scale * 0.8, color=(180, 180, 180))

    for o in tracks:
        color = color_for_id(o.track_id)

        if store is not None and show_trails:
            t = store.get(o.track_id)
            if t is not None:
                _draw_trail(image, t.trail, color, thickness)

        p1, p2 = (int(o.x1), int(o.y1)), (int(o.x2), int(o.y2))
        cv2.rectangle(image, p1, p2, color, thickness)
        fx, fy = o.bottom_center
        cv2.circle(image, (int(fx), int(fy)), thickness + 2, color, -1)   # ground point

        label = f"{o.label} #{o.track_id}"
        (tw, th), base = cv2.getTextSize(label, FONT, font_scale, 1)
        y_top = max(p1[1] - th - base, 0)
        cv2.rectangle(image, (p1[0], y_top), (p1[0] + tw, y_top + th + base), color, -1)
        cv2.putText(image, label, (p1[0], y_top + th), FONT, font_scale,
                    (0, 0, 0), 1, cv2.LINE_AA)
    return image


class FlashState:
    """Remembers when each rule last fired so overlays can flash for a moment."""

    def __init__(self, duration_s: float = 1.5):
        self.duration_s = duration_s
        self._last = {}

    def trigger(self, events, now: float) -> None:
        for e in events:
            self._last[e.rule_id] = now

    def active(self, rule_id: str, now: float) -> bool:
        t = self._last.get(rule_id)
        return t is not None and 0 <= now - t <= self.duration_s


def draw_zones(image: np.ndarray, rules: CameraRules, occupancy: dict,
               flash: FlashState, now: float, alpha: float = 0.25) -> np.ndarray:
    """Semi-transparent zone fills with outlines, names, and occupancy counts."""
    if not rules.zones:
        return image
    h, w = image.shape[:2]
    overlay = image.copy()
    shapes = []
    for z in rules.zones:
        pts = np.array([[x * w, y * h] for x, y in z.polygon], np.int32).reshape(-1, 1, 2)
        flashing = flash.active(z.id, now)
        color = FLASH_COLOR if flashing else ZONE_COLORS.get(z.type, (255, 200, 0))
        cv2.fillPoly(overlay, [pts], color)
        shapes.append((z, pts, color, flashing))

    cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

    for z, pts, color, flashing in shapes:
        cv2.polylines(image, [pts], True, color, 4 if flashing else 2, cv2.LINE_AA)
        x, y = pts[0][0]
        put_text(image, f"{z.name} [{occupancy.get(z.id, 0)}]",
                 (int(x) + 6, int(y) + 20), 0.55, color)
    return image


def draw_lines(image: np.ndarray, rules: CameraRules, counts: dict,
               flash: FlashState, now: float) -> np.ndarray:
    """Lines with a direction arrow (pointing toward the positive_direction side) and counters."""
    h, w = image.shape[:2]
    for ln in rules.lines:
        p1 = (int(ln.p1[0] * w), int(ln.p1[1] * h))
        p2 = (int(ln.p2[0] * w), int(ln.p2[1] * h))
        flashing = flash.active(ln.id, now)
        color = FLASH_COLOR if flashing else (0, 255, 255)
        cv2.line(image, p1, p2, color, 4 if flashing else 2, cv2.LINE_AA)

        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length              # normal toward the positive side
        mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
        tip = (int(mid[0] + nx * 45), int(mid[1] + ny * 45))
        cv2.arrowedLine(image, mid, tip, color, 2, tipLength=0.35)

        c = counts.get(ln.id, {"IN": 0, "OUT": 0})
        put_text(image, f"{ln.name}: arrow={ln.positive_direction}  "
                        f"IN {c['IN']}  OUT {c['OUT']}",
                 (p1[0] + 6, max(p1[1] - 8, 15)), 0.5, color)
    return image


def draw_event_feed(image: np.ndarray, lines, max_lines: int = 5) -> np.ndarray:
    """Most recent event descriptions, bottom-left."""
    recent = list(lines)[-max_lines:]
    h = image.shape[0]
    for i, text in enumerate(recent):
        y = h - 12 - (len(recent) - 1 - i) * 22
        put_text(image, text, (10, y), 0.55, (0, 215, 255))
    return image
