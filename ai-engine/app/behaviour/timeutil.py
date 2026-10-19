from datetime import datetime
from functools import lru_cache
from typing import Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


@lru_cache(maxsize=64)
def get_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(f"unknown time zone {name!r} (on Windows: pip install tzdata)") from e


def parse_hhmm(text) -> int:
    """'HH:MM' -> minutes since midnight."""
    try:
        h, m = str(text).split(":")
        h, m = int(h), int(m)
    except (ValueError, TypeError):
        raise ValueError(f"time must look like 'HH:MM', got {text!r}") from None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"time out of range: {text!r}")
    return h * 60 + m


def in_window(minutes: int, start: int, end: int) -> bool:
    """start inclusive, end exclusive; start > end means the window wraps past midnight."""
    if start < end:
        return start <= minutes < end
    return minutes >= start or minutes < end


def local_minutes_and_day(epoch: float, tz: ZoneInfo) -> Tuple[int, str]:
    dt = datetime.fromtimestamp(epoch, tz=tz)
    return dt.hour * 60 + dt.minute, DAYS[dt.weekday()]


def parse_clock_start(text: str, default_tz: ZoneInfo) -> float:
    """An ISO date-time ('2026-10-12T02:13:00', optionally with an offset) -> epoch seconds.
    A date-time without an offset is read in `default_tz` (the site time zone)."""
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt.timestamp()
