import time

import pytest

from app.db.events_repo import InMemoryEventRepository
from app.events.db_sink import PostgresEventSink
from app.events.envelope import envelope_from_event
from db_helpers import alert_event, plate_event, summary_event, zone_event

pytestmark = pytest.mark.slow


def test_five_thousand_mixed_events_are_stored_exactly_once_even_when_delivered_twice():
    repo = InMemoryEventRepository()
    sink = PostgresEventSink(repo)
    envs = []
    for i in range(5000):
        kind = i % 4
        e = (zone_event(i, track=i % 50), alert_event(i, alert_id=f"A{i}"), plate_event(i, plate=f"KA01AB{i % 9000:04d}"),
             summary_event(i, track=i % 50))[kind]
        envs.append(envelope_from_event(e, "RUN1"))
    t0 = time.time()
    for env in envs + envs:                                              # every event delivered twice
        sink.handle(env)
    assert repo.count_events() == 5000 and sink.stats["duplicates"] == 5000
    assert len(repo.list_alerts(limit=10**6)) == 1250
    print(f"\n5000 events x2 through the sink (in-memory): {time.time() - t0:.2f}s")
