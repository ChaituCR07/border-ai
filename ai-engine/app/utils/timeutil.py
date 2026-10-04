from datetime import datetime, timezone


def to_iso_utc(epoch_seconds: float) -> str:
    """Epoch seconds -> ISO 8601 UTC string ending in 'Z' (millisecond precision)."""
    dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
