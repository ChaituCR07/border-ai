"""
Quiescence Detector (Task 5.4).
Verifies that the entire pipeline has reached a settled state:
- Sink consumer group lag is 0
- Notification outbox has 0 pending items
- No new stream events for >= quiet_window_s
"""

import time
from typing import Callable, Optional


def wait_for_quiescence(
    check_status_fn: Callable[[], dict],
    quiet_window_s: float = 3.0,
    timeout_s: float = 45.0,
    poll_interval_s: float = 0.5,
) -> bool:
    start_time = time.time()
    quiet_since: Optional[float] = None
    last_event_count = -1

    while time.time() - start_time < timeout_s:
        status = check_status_fn()
        sink_lag = status.get("sink_lag", 0)
        pending_notifications = status.get("pending_notifications", 0)
        current_event_count = status.get("event_count", 0)

        is_drained = sink_lag == 0 and pending_notifications == 0

        if is_drained and current_event_count == last_event_count:
            if quiet_since is None:
                quiet_since = time.time()
            elif time.time() - quiet_since >= quiet_window_s:
                return True
        else:
            quiet_since = None
            last_event_count = current_event_count

        time.sleep(poll_interval_s)

    return False
