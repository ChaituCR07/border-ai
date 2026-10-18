from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path
from typing import List, Optional, Sequence

import cv2
import numpy as np

from app.identity.config import FaceConfig
from app.identity.embeddings import l2_normalize


@dataclass
class FaceDet:
    x1: float
    y1: float
    x2: float
    y2: float
    score: float
    landmarks: np.ndarray                         # (5, 2): right eye, left eye, nose, right mouth, left mouth
    raw: Optional[np.ndarray] = None              # engine-specific detector row (OpenCV alignment needs it)
    embedding: Optional[np.ndarray] = None        # set by engines that compute it during detection

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return max(self.width, 0.0) * max(self.height, 0.0)


class FaceEngine(ABC):
    model_name: str = "unknown"
    dim: int = 0

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[FaceDet]:
        """Faces in a BGR image, best first."""

    @abstractmethod
    def embed(self, image: np.ndarray, face: FaceDet) -> np.ndarray:
        """L2-normalized embedding of an aligned face."""


class OpenCvFaceEngine(FaceEngine):
    """YuNet detector + SFace recognizer through OpenCV (Option A)."""
    model_name = "sface-opencv"
    dim = 128

    def __init__(self, detector_path: Path, recognizer_path: Path, score_threshold: float = 0.8):
        self._det = cv2.FaceDetectorYN.create(str(detector_path), "", (320, 320), score_threshold, 0.3, 5000)
        self._rec = cv2.FaceRecognizerSF.create(str(recognizer_path), "")

    def detect(self, image: np.ndarray) -> List[FaceDet]:
        h, w = image.shape[:2]
        self._det.setInputSize((w, h))
        _, rows = self._det.detect(image)
        faces: List[FaceDet] = []
        if rows is None:
            return faces
        for row in rows:
            x, y, fw, fh = (float(v) for v in row[:4])
            faces.append(FaceDet(x, y, x + fw, y + fh, float(row[14]),
                                 np.asarray(row[4:14], np.float32).reshape(5, 2),
                                 raw=np.asarray(row, np.float32).reshape(1, -1)))
        return sorted(faces, key=lambda f: -(f.score * f.area))

    def embed(self, image: np.ndarray, face: FaceDet) -> np.ndarray:
        aligned = self._rec.alignCrop(image, face.raw)
        return l2_normalize(self._rec.feature(aligned))


class InsightFaceEngine(FaceEngine):
    """SCRFD + ArcFace through InsightFace (Option B). The pretrained packs are published for
    non-commercial research use: check their license before relying on them."""
    dim = 512

    def __init__(self, pack: str = "buffalo_l", use_gpu: bool = False, det_size=(320, 320)):
        from insightface.app import FaceAnalysis
        providers = (["CUDAExecutionProvider", "CPUExecutionProvider"] if use_gpu
                     else ["CPUExecutionProvider"])
        self._app = FaceAnalysis(name=pack, providers=providers)
        self._app.prepare(ctx_id=0 if use_gpu else -1, det_size=det_size)
        self.model_name = f"insightface-{pack}"

    def detect(self, image: np.ndarray) -> List[FaceDet]:
        faces = []
        for f in self._app.get(image):
            b = f.bbox
            faces.append(FaceDet(float(b[0]), float(b[1]), float(b[2]), float(b[3]), float(f.det_score),
                                 np.asarray(f.kps, np.float32), embedding=l2_normalize(f.normed_embedding)))
        return sorted(faces, key=lambda f: -(f.score * f.area))

    def embed(self, image: np.ndarray, face: FaceDet) -> np.ndarray:
        return face.embedding


class ScriptedFaceEngine(FaceEngine):
    """Returns one fixed frontal face per call with the next embedding from a list (tests and dry runs)."""
    model_name = "scripted"

    def __init__(self, embeddings: Sequence[np.ndarray], model_name: str = "scripted"):
        self._embeddings = cycle([l2_normalize(e) for e in embeddings])
        self.model_name = model_name
        self.dim = len(np.asarray(embeddings[0]).reshape(-1))
        self.calls = 0

    def detect(self, image: np.ndarray) -> List[FaceDet]:
        self.calls += 1
        landmarks = np.array([[30, 40], [70, 40], [50, 60], [35, 80], [65, 80]], np.float32)
        return [FaceDet(20, 20, 80, 90, 0.99, landmarks, embedding=next(self._embeddings))]

    def embed(self, image: np.ndarray, face: FaceDet) -> np.ndarray:
        return face.embedding


# ----------------------------------------------------------------------------- quality gate
@dataclass
class FaceQuality:
    ok: bool
    reason: str
    score: float            # 0-1, used as the weight when combining embeddings
    size_px: float
    sharpness: float
    yaw_ratio: float


def yaw_ratio(landmarks: np.ndarray) -> float:
    """Horizontal nose offset from the eye midpoint, relative to the eye distance.
    About 0 for a frontal face; grows as the head turns toward profile."""
    eye_r, eye_l, nose = landmarks[0], landmarks[1], landmarks[2]
    eye_dist = max(abs(float(eye_l[0] - eye_r[0])), 1e-6)
    return float((nose[0] - (eye_r[0] + eye_l[0]) / 2.0) / eye_dist)


def face_quality(image: np.ndarray, face: FaceDet, cfg: FaceConfig) -> FaceQuality:
    size = float(min(face.width, face.height))
    yaw = yaw_ratio(face.landmarks)
    h, w = image.shape[:2]
    x1, y1 = max(0, int(face.x1)), max(0, int(face.y1))
    x2, y2 = min(w, int(face.x2)), min(h, int(face.y2))
    sharp = 0.0
    if x2 - x1 >= 4 and y2 - y1 >= 4:
        gray = cv2.cvtColor(cv2.resize(image[y1:y2, x1:x2], (64, 64)), cv2.COLOR_BGR2GRAY)
        sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    score = (0.4 * min(1.0, size / 100.0) + 0.3 * min(1.0, sharp / 150.0)
             + 0.3 * max(0.0, 1.0 - abs(yaw) / max(cfg.max_yaw_ratio, 1e-6)))
    if face.score < cfg.detector_score:
        return FaceQuality(False, "low_score", score, size, sharp, yaw)
    if size < cfg.min_face_px:
        return FaceQuality(False, "too_small", score, size, sharp, yaw)
    if abs(yaw) > cfg.max_yaw_ratio:
        return FaceQuality(False, "profile", score, size, sharp, yaw)
    if sharp < cfg.min_sharpness:
        return FaceQuality(False, "blurry", score, size, sharp, yaw)
    return FaceQuality(True, "", score, size, sharp, yaw)
