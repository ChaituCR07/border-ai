import hashlib
import os
from typing import Optional


def compute_file_sha256(path: str) -> Optional[str]:
    """Computes SHA256 hex digest of a file. Returns None if file does not exist."""
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()
