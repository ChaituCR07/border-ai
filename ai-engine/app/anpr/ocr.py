import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import cycle
from typing import List, Optional, Sequence

import numpy as np

from app.anpr.types import OcrResult


@dataclass
class _Piece:
    text: str
    conf: float
    cx: Optional[float] = None       # box center, used to restore reading order
    cy: Optional[float] = None
    h: Optional[float] = None


def assemble(pieces: Sequence[_Piece]) -> OcrResult:
    """Combine OCR text pieces into one string in reading order (top to bottom, then left to
    right, which handles two-line plates). Confidence is the length-weighted mean."""
    items = [p for p in pieces if p.text and p.text.strip()]
    if not items:
        return OcrResult("", 0.0, [])

    if all(p.cy is not None for p in items):
        items = sorted(items, key=lambda p: p.cy)
        lines, cur = [], [items[0]]
        for p in items[1:]:
            tol = 0.6 * max(p.h or 0.0, cur[-1].h or 0.0)
            if p.cy - cur[-1].cy > tol:
                lines.append(cur)
                cur = [p]
            else:
                cur.append(p)
        lines.append(cur)
        items = [p for line in lines for p in sorted(line, key=lambda p: p.cx or 0.0)]

    total = sum(len(p.text.strip()) for p in items)
    conf = sum(p.conf * len(p.text.strip()) for p in items) / max(total, 1)
    return OcrResult("".join(p.text.strip() for p in items), float(conf),
                     [(p.text.strip(), float(p.conf)) for p in items])


def _center_height(poly) -> tuple:
    a = np.asarray(poly, dtype=float)
    if a.shape == (4,):                                    # [x1, y1, x2, y2]
        return (a[0] + a[2]) / 2, (a[1] + a[3]) / 2, a[3] - a[1]
    return a[:, 0].mean(), a[:, 1].mean(), a[:, 1].max() - a[:, 1].min()


def parse_v2_result(raw) -> List[_Piece]:
    """PaddleOCR 2.x: ocr.ocr(img) -> [ [ [box, (text, conf)], ... ] ] (None when nothing is found)."""
    if not raw or raw[0] is None:
        return []
    pieces = []
    for line in raw[0]:
        box, (text, conf) = line[0], line[1]
        cx, cy, h = _center_height(box)
        pieces.append(_Piece(text, float(conf), cx, cy, h))
    return pieces


def _get(res, key, default=None):
    try:
        val = res[key]
        if val is not None:
            return val
    except Exception:
        pass
    try:
        val = getattr(res, key, None)
        if val is not None:
            return val
    except Exception:
        pass
    try:
        return res.json["res"].get(key, default)
    except Exception:
        return default


def parse_v3_result(res) -> List[_Piece]:
    """PaddleOCR 3.x: one result object per image with rec_texts, rec_scores, and box lists."""
    texts = _get(res, "rec_texts", []) or []
    scores = _get(res, "rec_scores", []) or []
    polys = _get(res, "rec_polys")
    if polys is None:
        polys = _get(res, "rec_boxes")
    pieces = []
    for i, text in enumerate(texts):
        conf = float(scores[i]) if i < len(scores) else 0.0
        if polys is not None and i < len(polys):
            cx, cy, h = _center_height(polys[i])
            pieces.append(_Piece(text, conf, cx, cy, h))
        else:
            pieces.append(_Piece(text, conf))
    return pieces


class OcrEngine(ABC):
    @abstractmethod
    def read(self, image: np.ndarray) -> OcrResult:
        """image: BGR uint8. Returns the plate text in reading order and a 0-1 confidence."""


class PaddleOcrEngine(OcrEngine):
    def __init__(self, lang: str = "en", device: str = "cpu"):
        from importlib.metadata import version
        self.version = version("paddleocr")
        self.major = int(self.version.split(".")[0])
        self.lang, self.device = lang, device
        self._load()

    def _load(self) -> None:
        from paddleocr import PaddleOCR
        if self.major >= 3:
            kwargs = dict(lang=self.lang, use_doc_orientation_classify=False,
                          use_doc_unwarping=False, use_textline_orientation=False,
                          device=self.device)
            try:
                self._ocr = PaddleOCR(**kwargs)
            except TypeError:                              # a parameter name differs in version
                kwargs.pop("device", None)
                self._ocr = PaddleOCR(**kwargs)
        else:
            self._ocr = PaddleOCR(use_angle_cls=False, lang=self.lang,
                                  use_gpu=(self.device != "cpu"), show_log=False)

    def read(self, image: np.ndarray) -> OcrResult:
        if self.major >= 3:
            pieces: List[_Piece] = []
            for res in self._ocr.predict(image):
                pieces += parse_v3_result(res)
        else:
            pieces = parse_v2_result(self._ocr.ocr(image, cls=False))
        return assemble(pieces)


class HttpOcrEngine(OcrEngine):
    """Talks to scripts/ocr_server.py running in a separate environment (Option B)."""

    def __init__(self, url: str = "http://127.0.0.1:8100/ocr", timeout: float = 5.0):
        import httpx
        self._client = httpx.Client(timeout=timeout)
        self.url = url

    def read(self, image: np.ndarray) -> OcrResult:
        import cv2
        ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        r = self._client.post(self.url, files={"file": ("plate.jpg", io.BytesIO(buf.tobytes()), "image/jpeg")})
        r.raise_for_status()
        d = r.json()
        return OcrResult(d["text"], float(d["confidence"]), [tuple(x) for x in d.get("lines", [])])


class ScriptedOcrEngine(OcrEngine):
    """Returns a fixed sequence of texts (cycling). For tests and dry runs (engine: fake)."""

    def __init__(self, texts: Sequence[str], confidence: float = 0.9):
        self._texts = cycle(texts)
        self.confidence = confidence

    def read(self, image: np.ndarray) -> OcrResult:
        text = next(self._texts)
        return OcrResult(text, self.confidence, [(text, self.confidence)])
