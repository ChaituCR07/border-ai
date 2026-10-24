import json
import threading
import time

import pytest

from app.events.publisher import EventPublisher, StreamTransport
from app.events.streams import InMemoryStreamClient
from events_helpers import ev, make_events_cfg, wait_until


def make(client=None, **cfg_kw):
    client = client or InMemoryStreamClient()
    cfg = make_events_cfg(**cfg_kw)
    return EventPublisher(StreamTransport(client, cfg), cfg, run_id="RUN1"), client, cfg


def ids(client, stream, count=10000):
    return [json.loads(f["data"])["event_id"] for _, f in client.range(stream, count)]


def json_events(client, stream):
    return [json.loads(f["data"]) for _, f in client.range(stream, 10000)]


def test_events_arrive_in_order_with_the_run_id():
    pub, client, cfg = make()
    events = [ev(i) for i in range(50)]
    pub.start()
    for e in events:
        assert pub.publish(e) is True
    pub.stop(drain=True)
    assert ids(client, cfg.stream) == [e.event_id for e in events]
    first = client.range(cfg.stream, 1)[0][1]
    assert first["run_id"] == "RUN1" and first["camera"] == "CAM_1" and first["v"] == "1"
    assert pub.status()["published"] == 50 and pub.status()["connected"] is True


def test_alerts_are_copied_to_the_alerts_stream():
    pub, client, cfg = make()
    pub.start()
    pub.publish(ev(1, "ZONE_VIOLATION"))
    alert = ev(2, "THREAT_ALERT", severity="HIGH")
    pub.publish(alert)
    pub.stop(drain=True)
    assert len(ids(client, cfg.stream)) == 2
    assert ids(client, cfg.alerts_stream) == [alert.event_id]


def test_an_outage_buffers_events_and_recovery_delivers_them_in_order():
    pub, client, cfg = make()
    client.down = True
    pub.start()
    events = [ev(i) for i in range(30)]
    for e in events:
        pub.publish(e)
    assert wait_until(lambda: not pub.status()["connected"])
    assert pub.status()["retries"] >= 1 and pub.status()["queued_high"] + pub.status()["queued_low"] == 30
    client.down = False
    pub.stop(drain=True, timeout=5)
    assert ids(client, cfg.stream) == [e.event_id for e in events]
    assert pub.status()["connected"] is True


def test_publishing_never_blocks_during_an_outage_and_memory_is_bounded():
    pub, client, cfg = make()
    client.down = True
    pub.start()
    events = [ev(i, "ZONE_ENTER") for i in range(5000)]
    t0 = time.time()
    for e in events:
        pub.publish(e)
    assert time.time() - t0 < 5.0
    s = pub.status()
    assert s["queued_low"] <= cfg.buffer_low and s["dropped_low"] >= 5000 - cfg.buffer_low
    pub.stop(drain=False)


def test_noisy_events_are_dropped_before_precious_ones_and_order_is_kept():
    pub, client, cfg = make(buffer_low=100, buffer_high=50)
    client.down = True
    pub.start()
    precious = []
    for i in range(200):
        pub.publish(ev(i, "ZONE_ENTER"))
        if i % 20 == 0:
            alert = ev(i, "THREAT_ALERT", severity="HIGH")
            precious.append(alert.event_id)
            pub.publish(alert)
    s = pub.status()
    assert s["dropped_high"] == 0 and s["dropped_low"] >= 100
    client.down = False
    pub.stop(drain=True, timeout=5)
    delivered = json_events(client, cfg.stream)
    assert [e["event_id"] for e in delivered if e["type"] == "THREAT_ALERT"] == precious       # none lost
    times = [e["timestamp"] for e in delivered]
    assert times == sorted(times)                                                            # global order preserved


def test_when_the_precious_buffer_overflows_the_oldest_precious_events_go():
    pub, client, cfg = make(buffer_high=5)
    client.down = True
    pub.start()
    for i in range(12):
        pub.publish(ev(i, "THREAT_ALERT", severity="HIGH"))
    assert pub.status()["dropped_high"] >= 7 and pub.status()["queued_high"] <= 5
    pub.stop(drain=False)


def test_shutdown_with_the_bus_still_down_does_not_hang_and_counts_what_was_left():
    pub, client, cfg = make()
    client.down = True
    pub.start()
    for i in range(20):
        pub.publish(ev(i))
    t0 = time.time()
    pub.stop(drain=True, timeout=0.3)
    assert time.time() - t0 < 5.0
    assert pub.status()["dropped_on_shutdown"] == 20


def test_a_failure_in_the_middle_of_a_batch_causes_duplicates_not_losses():
    pub, client, cfg = make(batch_size=10)
    events = [ev(i) for i in range(10)]
    client.fail_after_adds = 3                                    # three entries get in, then the send fails
    pub.start()
    for e in events:
        pub.publish(e)
    pub.stop(drain=True, timeout=5)
    delivered = ids(client, cfg.stream)
    assert set(delivered) == {e.event_id for e in events} and len(delivered) >= len(events)   # duplicates are allowed, losses are not


def test_many_producer_threads_lose_nothing_and_keep_their_own_order():
    pub, client, cfg = make(buffer_low=100000, buffer_high=100000)
    pub.start()
    per_thread = {t: [ev(i, track=t) for i in range(200)] for t in range(8)}

    def feed(t):
        for e in per_thread[t]:
            pub.publish(e)

    threads = [threading.Thread(target=feed, args=(t,)) for t in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    pub.stop(drain=True, timeout=10)
    delivered = json_events(client, cfg.stream)
    assert len(delivered) == 1600
    for t in range(8):
        assert [e["event_id"] for e in delivered if e["track_id"] == t] == [e.event_id for e in per_thread[t]]


def test_a_bad_event_does_not_stop_the_publisher(monkeypatch):
    import app.events.publisher as module
    real = module.envelope_from_event

    def flaky(event, run_id=""):
        if event.rule_id == "R3":
            raise ValueError("cannot serialize")
        return real(event, run_id)

    monkeypatch.setattr(module, "envelope_from_event", flaky)
    pub, client, cfg = make()
    pub.start()
    for i in range(6):
        pub.publish(ev(i))
    pub.stop(drain=True)
    assert len(ids(client, cfg.stream)) == 5 and pub.status()["invalid_events"] == 1


def test_publish_never_raises_for_junk():
    pub, _, _ = make()
    assert pub.publish(None) is False
    assert pub.status()["publish_errors"] == 1
