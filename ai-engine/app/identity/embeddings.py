import numpy as np


def l2_normalize(v) -> np.ndarray:
    a = np.asarray(v, dtype=np.float32).reshape(-1)
    n = float(np.linalg.norm(a))
    if not np.isfinite(n) or n < 1e-12:
        raise ValueError("embedding has zero or invalid norm")
    return (a / n).astype(np.float32)


def cosine(a, b) -> float:
    return float(np.dot(l2_normalize(a), l2_normalize(b)))


def to_bytes(v) -> bytes:
    return np.asarray(v, dtype="<f4").tobytes()


def from_bytes(data, dim=None) -> np.ndarray:
    arr = np.frombuffer(bytes(data), dtype="<f4").astype(np.float32)
    if dim is not None and arr.size != dim:
        raise ValueError(f"stored embedding has {arr.size} values, expected {dim}")
    return arr


def validate_embedding(v, min_dim: int = 64, max_dim: int = 2048) -> np.ndarray:
    """A usable embedding: one-dimensional, finite, plausible length. Returns it L2-normalized."""
    a = np.asarray(v, dtype=np.float32)
    if a.ndim != 1 or not (min_dim <= a.size <= max_dim) or not np.all(np.isfinite(a)):
        raise ValueError(f"embedding must be a finite 1-D vector of {min_dim}-{max_dim} values")
    return l2_normalize(a)
