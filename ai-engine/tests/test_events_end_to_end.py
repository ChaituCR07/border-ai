import json
import random

from app.events.processor import EventProcessor, MemorySink
from app.events.publisher import EventPublisher, StreamTransport
from app.events.streams import InMemoryStreamClient
from events_helpers import drain, ev, make_events_cfg, wait_until

TYPES = ["ZONE_ENTER", "ZONE_EXIT", "LINE_CROSSING", "PLATE_RECOGNIZED", "ZONE_VIOLATION", "THREAT_ALERT"]


def build(cfg_kw=None):
    client = InMemoryStreamClient()
    cfg = make_events_cfg(**(cfg_kw or {}))
    return EventPublisher(StreamTransport(client, cfg), cfg, "RUN1"), client, cfg, EventProcessor(client, [MemorySink()], cfg)


def test_no_loss_and_no_duplicate_effects_through_outages_and_partial_failures():
    pub, client, cfg, proc = build({"buffer_low": 100000, "buffer_high": 100000})
    rng = random.Random(7)
    events = [ev(i, rng.choice(TYPES), cam=f"CAM_{rng.randint(1, 3)}", track=rng.randint(1, 20)) for i in range(600)]
    pub.start()
    for i, e in enumerate(events):
        if i == 100:
            client.down = True                                     # an outage in the middle
        if i == 250:
            client.down = False
            client.fail_after_adds = 4                             # and a partial failure right after it
        pub.publish(e)
    pub.stop(drain=True, timeout=10)
    drain(proc, rounds=200)
    sink = proc.sinks[0]
    assert sorted(sink.ids) == sorted(e.event_id for e in events)  # every event exactly once at the sink
    assert len(sink.ids) == len(set(sink.ids)) == 600
    assert client.length(cfg.stream) >= 600                         # the stream itself may hold duplicates
    assert proc.status().get("dead_lettered", 0) == 0 and client.pending_count(cfg.stream, cfg.processor.group) == 0


def test_alerts_reach_the_alerts_stream_exactly_like_the_main_stream():
    pub, client, cfg, _ = build()
    alerts = [ev(i, "THREAT_ALERT", severity="CRITICAL") for i in range(5)]
    pub.start()
    for i in range(30):
        pub.publish(ev(100 + i, "ZONE_ENTER"))
    for a in alerts:
        pub.publish(a)
    pub.stop(drain=True)
    delivered = [json.loads(f["data"])["event_id"] for _, f in client.range(cfg.alerts_stream, 100)]
    assert delivered == [a.event_id for a in alerts]
