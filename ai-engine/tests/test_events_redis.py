import json
import time
import uuid

import pytest

from app.events.config import EventsConfig, ProcessorConfig
from app.events.processor import EventProcessor, MemorySink
from app.events.publisher import EventPublisher, StreamTransport
from app.events.streams import RedisStreamClient
from events_helpers import drain, ev

pytestmark = pytest.mark.redis


@pytest.fixture
def redis_setup(redis_url):
    prefix = f"test.{uuid.uuid4().hex[:8]}"
    cfg = EventsConfig(enabled=True, stream=prefix, alerts_stream=f"{prefix}.alerts", dead_stream=f"{prefix}.dead",
                       batch_size=10, flush_ms=5, retry_initial_s=0.05, retry_max_s=0.2, shutdown_timeout_s=3,
                       processor=ProcessorConfig(block_ms=50, batch=20, reclaim_idle_ms=60, reclaim_every_s=0.0,
                                                 max_deliveries=3))
    client = RedisStreamClient.from_url(redis_url)
    yield client, cfg
    for name in (cfg.stream, cfg.alerts_stream, cfg.dead_stream):
        try:
            client.delete(name)
        except Exception:
            pass


def test_publisher_to_processor_over_real_redis(redis_setup):
    client, cfg = redis_setup
    pub = EventPublisher(StreamTransport(client, cfg), cfg, "RUN1")
    pub.start()
    events = [ev(i, "THREAT_ALERT" if i % 10 == 0 else "ZONE_VIOLATION", severity="HIGH") for i in range(50)]
    for e in events:
        pub.publish(e)
    pub.stop(drain=True, timeout=5)

    assert client.length(cfg.stream) == 50 and client.length(cfg.alerts_stream) == 5
    proc = EventProcessor(client, [MemorySink()], cfg)
    drain(proc)
    assert proc.sinks[0].ids == [e.event_id for e in events]
    assert client.pending_count(cfg.stream, cfg.processor.group) == 0


def test_duplicates_and_poison_messages_over_real_redis(redis_setup):
    client, cfg = redis_setup
    proc = EventProcessor(client, [MemorySink()], cfg)
    from events_helpers import env
    good = env(1)
    client.xadd(cfg.stream, good.to_fields())
    client.xadd(cfg.stream, good.to_fields())                                  # a duplicate delivery
    bad = good.to_fields()
    bad["v"] = "99"
    client.xadd(cfg.stream, bad)                                               # an unsupported version
    drain(proc)
    assert proc.sinks[0].ids == [good.event_id]
    dead = client.range(cfg.dead_stream, 10)
    assert len(dead) == 1 and "unsupported_version" in dead[0][1]["dead_reason"]
    assert client.pending_count(cfg.stream, cfg.processor.group) == 0


def test_a_second_consumer_takes_over_after_a_crash_over_real_redis(redis_setup):
    client, cfg = redis_setup
    from events_helpers import env
    client.group_create(cfg.stream, cfg.processor.group)
    envs = [env(i) for i in range(5)]
    for e in envs:
        client.xadd(cfg.stream, e.to_fields())
    client.read_group(cfg.stream, cfg.processor.group, "dead-consumer", count=10)        # read, never acknowledged
    time.sleep(0.15)
    proc = EventProcessor(client, [MemorySink()], cfg, consumer="rescuer")
    drain(proc)
    assert sorted(proc.sinks[0].ids) == sorted(e.event_id for e in envs)
    assert client.pending_count(cfg.stream, cfg.processor.group) == 0
