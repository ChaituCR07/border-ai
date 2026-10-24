from typing import List

STATUSES = ("NEW", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "FALSE_POSITIVE")
OPEN = ("NEW", "ACKNOWLEDGED", "IN_PROGRESS")
TERMINAL = ("RESOLVED", "FALSE_POSITIVE")

ALLOWED = {
    "NEW": ("ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "FALSE_POSITIVE"),
    "ACKNOWLEDGED": ("IN_PROGRESS", "RESOLVED", "FALSE_POSITIVE"),
    "IN_PROGRESS": ("RESOLVED", "FALSE_POSITIVE"),
    "RESOLVED": (),
    "FALSE_POSITIVE": (),
}


class AlertNotFound(LookupError):
    pass


class InvalidTransition(ValueError):
    pass


def sources_for(to_status: str) -> List[str]:
    """Statuses from which an alert may move to `to_status`."""
    return [s for s, targets in ALLOWED.items() if to_status in targets]
