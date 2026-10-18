from collections import OrderedDict
from typing import Hashable

from app.watchlist.models import STATUS_RANK


class CooldownTracker:
    """Suppress repeats per key inside `cooldown_s`, but always let a STRONGER status through
    (the same rule Day 9's WatchlistService applies to plates)."""

    def __init__(self, cooldown_s: float, max_keys: int = 5000):
        self.cooldown_s = cooldown_s
        self.max_keys = max_keys
        self._last: "OrderedDict[Hashable, tuple]" = OrderedDict()

    def allow(self, key: Hashable, status: str, timestamp: float) -> bool:
        last = self._last.get(key)
        if (last is not None and (timestamp - last[0]) < self.cooldown_s
                and STATUS_RANK[status] <= STATUS_RANK[last[1]]):
            return False
        self._last[key] = (timestamp, status)
        self._last.move_to_end(key)
        while len(self._last) > self.max_keys:
            self._last.popitem(last=False)
        return True
