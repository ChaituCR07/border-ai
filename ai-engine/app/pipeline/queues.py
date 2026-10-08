import queue
import threading
from typing import Any


def put_drop_oldest(q: "queue.Queue", item: Any) -> bool:
    """Put `item`; if the queue is full, discard the oldest entries to make room.
    Returns True if anything was dropped."""
    dropped = False
    while True:
        try:
            q.put_nowait(item)
            return dropped
        except queue.Full:
            try:
                q.get_nowait()
                dropped = True
            except queue.Empty:
                pass


def put_blocking(q: "queue.Queue", item: Any, stop: threading.Event,
                 poll_s: float = 0.1) -> bool:
    """Backpressure: wait for room. Returns False if `stop` was set before the item fit."""
    while not stop.is_set():
        try:
            q.put(item, timeout=poll_s)
            return True
        except queue.Full:
            continue
    return False
