import logging
from collections import Counter

from app.db.events_repo import EventRepository, InvalidRecord
from app.db.records import MappingError, map_envelope
from app.events.envelope import Envelope
from app.events.processor import EventSink, PermanentSinkError

log = logging.getLogger("events.db_sink")


class PostgresEventSink(EventSink):
    """Stores each envelope as rows. Idempotent: a repeated event_id changes nothing.
    Bad data -> PermanentSinkError (dead letter). A database outage -> the repository's RepoUnavailable propagates,
    which the processor treats as 'try again later'."""

    def __init__(self, repo: EventRepository):
        self.repo = repo
        self.stats: Counter = Counter()

    def handle(self, env: Envelope) -> None:
        try:
            record = map_envelope(env)
        except (MappingError, KeyError, TypeError, ValueError) as e:
            raise PermanentSinkError(f"mapping: {e}") from None
        try:
            result = self.repo.store(record)
        except InvalidRecord as e:
            raise PermanentSinkError(f"invalid_record: {e}") from None
        if not result.inserted:
            self.stats["duplicates"] += 1
            return
        self.stats["stored"] += 1
        for flag, label in ((result.alert_created, "alerts"), (result.vehicle_created, "vehicles"),
                            (result.detection_created, "detections"), (result.camera_registered, "cameras_registered")):
            if flag:
                self.stats[label] += 1
        if result.camera_registered:
            log.warning("Camera %s was not seeded: registered a placeholder (status UNREGISTERED)", env.camera)
