import os
import tempfile

try:
    import cv2
except ImportError:
    cv2 = None


def save_snapshot_atomic(frame, rel_path: str, root: str, quality: int = 85) -> str:
    """
    Save an evidence frame atomically:
    1. Writes to a temporary file on the same filesystem.
    2. Flushes and calls fsync to guarantee disk persistence.
    3. Renames atomically to final destination.
    4. Cleans up temp file on any error.
    """
    if ".." in rel_path.replace("\\", "/").split("/"):
        raise ValueError(f"Path traversal not permitted: {rel_path}")

    final = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(final), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(final), suffix=".tmp")
    try:
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise RuntimeError("JPEG encode failed")
        with os.fdopen(fd, "wb") as f:
            f.write(buf.tobytes())
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, final)
        return rel_path
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
