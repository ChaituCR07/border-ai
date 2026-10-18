from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence, Tuple

import cv2
import numpy as np

from app.identity.embeddings import l2_normalize


class PersonEmbedder(ABC):
    name: str = "unknown"

    @abstractmethod
    def embed(self, crop: np.ndarray) -> np.ndarray:
        """L2-normalized appearance embedding of a BGR person crop."""


class ColorLayoutEmbedder(PersonEmbedder):
    """Hellinger-normalized HSV histograms of the torso and legs (after gray-world color correction).
    Cosine similarity of two embeddings is the average Bhattacharyya overlap of their histograms."""
    name = "color-layout"

    @staticmethod
    def _gray_world(img: np.ndarray) -> np.ndarray:
        f = img.astype(np.float32)
        means = f.reshape(-1, 3).mean(axis=0)
        gain = means.mean() / np.maximum(means, 1e-6)
        return np.clip(f * gain, 0, 255).astype(np.uint8)

    def embed(self, crop: np.ndarray) -> np.ndarray:
        img = self._gray_world(cv2.resize(crop, (64, 128), interpolation=cv2.INTER_AREA))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        parts = []
        for r0, r1 in ((0.15, 0.55), (0.55, 1.0)):                       # torso, legs
            region = hsv[int(128 * r0):int(128 * r1), 8:56]              # trim the sides (background)
            hs = cv2.calcHist([region], [0, 1], None, [16, 8], [0, 180, 0, 256]).flatten()
            v = cv2.calcHist([region], [2], None, [8], [0, 256]).flatten()
            for hist in (hs, v):
                parts.append(np.sqrt(hist / max(float(hist.sum()), 1e-9)))
        return l2_normalize(np.concatenate(parts))


class OnnxPersonEmbedder(PersonEmbedder):
    """A Re-ID network supplied as ONNX (for example an OSNet export). Input size is (width, height)."""

    def __init__(self, path: Path, size: Tuple[int, int] = (128, 256),
                 mean: Sequence[float] = (0.485, 0.456, 0.406), std: Sequence[float] = (0.229, 0.224, 0.225)):
        self._net = cv2.dnn.readNetFromONNX(str(path))
        self.size = (int(size[0]), int(size[1]))
        self.mean = np.array(mean, np.float32)
        self.std = np.array(std, np.float32)
        self.name = f"onnx-{Path(path).stem}"

    def embed(self, crop: np.ndarray) -> np.ndarray:
        img = cv2.resize(crop, self.size, interpolation=cv2.INTER_LINEAR)
        rgb = (cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0 - self.mean) / self.std
        self._net.setInput(rgb.transpose(2, 0, 1)[None].astype(np.float32))
        return l2_normalize(self._net.forward())
