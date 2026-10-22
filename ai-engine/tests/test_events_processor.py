import json
import threading
import time

import pytest

from app.events.processor import (EventProcessor, EventSink, JsonlFileSink, MemorySink, PermanentSinkError)
from app.events.streams import InMemoryStreamClient
from events_helpers import drain, env, make_events_cfg


class Crash(BaseException):
    """A hard crash: not an Exception, so the processor must not swallow it."""


class ScriptedSink(EventSink):
    def __init__(self, failures=0, error=RuntimeError, permanent_on=None):
        self.failures, self.error, self.permanent_on = failures, error, permanent_on
        self.calls, self.done = 0, []

    def handle(self, e):
        self.calls += 1
        if self.permanent_on and e.event_id == self.permanent_on:
            raise PermanentSinkError("cannot ever work")
        if self.failures > 0:
            self.failures -= 1
            raise self.error("temporary problem")
        self.done.append(e.event_id)


def setup(sinks=None, client=None, **cfg_kw):
    client = client or InMemoryStreamClient()
    cfg = make_events_cfg(**cfg_kw)
    sinks = sinks if sinks is not None else [MemorySink()]
    return EventProcessor(client, sinks, cfg), client, cfg, sinks


def publish(client, cfg, envelopes):
    for e in envelopes:
        client.xadd(cfg.stream, e.to_fields())


def idle_wait():
    time.sleep(0.12)                                              # longer than reclaim_idle_ms (50 ms)


def test_valid_events_are_handled_and_acknowledged():
    proc, client, cfg, (sink,) = setup()
    envs = [env(i) for i in range(5)]
    publish(client, cfg, envs)
    assert proc.run_once() == 5
    assert sink.ids == [e.event_id for e in envs]
    assert client.pending_count(cfg.stream, cfg.processor.group) == 0 and proc.status()["processed"] == 5


def test_duplicates_are_acknowledged_but_handled_once():
    proc, client, cfg, (sink,) = setup()
    e1, e2 = env(1), env(2)
    publish(client, cfg, [e1, e1, e2, e1])
    drain(proc)
    assert len(sink.ids) == 2 and sink.ids == [e1.event_id, e2.event_id]
    assert proc.status()["duplicates"] == 2 and client.pending_count(cfg.stream, cfg.processor.group) == 0


@pytest.mark.parametrize("mutate, reason", [
    (lambda f: f.update(v="9"), "unsupported_version"),
    (lambda f: f.pop("data"), "missing_data"),
    (lambda f: f.update(type="not valid"), "invalid_type"),
])
def test_invalid_messages_go_to_the_dead_letter_stream_and_do_not_block_the_rest(mutate, reason):
    proc, client, cfg, (sink,) = setup()
    bad = env(1).to_fields()
    mutate(bad)
    client.xadd(cfg.stream, bad)
    publish(client, cfg, [env(2)])
    drain(proc)
    dead = client.range(cfg.dead_stream, 10)
    assert len(dead) == 1 and reason in dead[0][1]["dead_reason"] and dead[0][1]["dead_reason"].startswith("invalid:")
    assert dead[0][1]["origin_id"] and dead[0][1]["group"] == cfg.processor.group
    assert len(sink.ids) == 1 and client.pending_count(cfg.stream, cfg.processor.group) == 0


def test_a_permanent_sink_error_is_dead_lettered_immediately():
    bad = env(1)
    sink = ScriptedSink(permanent_on=bad.event_id)
    proc, client, cfg, _ = setup([sink])
    publish(client, cfg, [bad, env(2)])
    drain(proc)
    assert [f["event_id"] for _, f in client.range(cfg.dead_stream, 10)] == [bad.event_id]
    assert len(sink.done) == 1 and client.pending_count(cfg.stream, cfg.processor.group) == 0


def test_a_transient_failure_is_retried_after_the_idle_time_and_then_succeeds():
    sink = ScriptedSink(failures=2)
    proc, client, cfg, _ = setup([sink])
    e = env(1)
    publish(client, cfg, [e])
    proc.run_once()
    assert sink.done == [] and client.pending_count(cfg.stream, cfg.processor.group) == 1      # failed, left pending
    idle_wait()
    proc.run_once()                                                                             # second attempt fails
    idle_wait()
    proc.run_once()                                                                             # third attempt succeeds
    assert sink.done == [e.event_id] and client.pending_count(cfg.stream, cfg.processor.group) == 0
    assert client.length(cfg.dead_stream) == 0 and proc.status()["sink_failures"] == 2


def test_a_message_that_keeps_failing_is_dead_lettered_after_max_deliveries():
    sink = ScriptedSink(failures=100)
    proc, client, cfg, _ = setup([sink])
    publish(client, cfg, [env(1)])
    for _ in range(cfg.processor.max_deliveries):
        proc.run_once()
        idle_wait()
    dead = client.range(cfg.dead_stream, 10)
    assert len(dead) == 1 and dead[0][1]["dead_reason"].startswith("failed_3_times")
    assert client.pending_count(cfg.stream, cfg.processor.group) == 0 and sink.calls == 3


def test_a_message_is_acknowledged_only_after_every_sink_succeeded():
    ok, flaky = ScriptedSink(), ScriptedSink(failures=1)
    proc, client, cfg, _ = setup([ok, flaky])
    publish(client, cfg, [env(1)])
    proc.run_once()
    assert ok.calls == 1 and client.pending_count(cfg.stream, cfg.processor.group) == 1
    idle_wait()
    proc.run_once()
    assert flaky.done and client.pending_count(cfg.stream, cfg.processor.group) == 0
    assert ok.calls == 2                                          # the first sink saw it twice: sinks must be idempotent


def test_the_file_sink_is_idempotent(tmp_path):
    sink = JsonlFileSink(tmp_path / "out.jsonl")
    e1, e2 = env(1), env(2)
    for _ in range(3):
        sink.handle(e1)
    sink.handle(e2)
    sink.close()
    lines = (tmp_path / "out.jsonl").read_text().splitlines()
    assert len(lines) == 2 and [json.loads(l)["event_id"] for l in lines] == [e1.event_id, e2.event_id]


def test_a_crashed_consumer_does_not_lose_messages():
    class CrashingSink(EventSink):
        def __init__(self):
            self.n, self.done = 0, []

        def handle(self, e):
            self.n += 1
            if self.n == 3:
                raise Crash()
            self.done.append(e.event_id)

    client = InMemoryStreamClient()
    cfg = make_events_cfg()
    envs = [env(i) for i in range(10)]
    publish(client, cfg, envs)

    crashing = CrashingSink()
    a = EventProcessor(client, [crashing], cfg, consumer="a")
    with pytest.raises(Crash):
        a.run_once()                                              # dies while handling the third message
    assert len(crashing.done) == 2

    survivor = MemorySink()
    b = EventProcessor(client, [survivor], cfg, consumer="b")
    idle_wait()
    drain(b)
    assert set(crashing.done) | set(survivor.ids) == {e.event_id for e in envs}
    assert client.pending_count(cfg.stream, cfg.processor.group) == 0


def test_consumers_in_one_group_share_the_work_without_overlap():
    client = InMemoryStreamClient()
    cfg = make_events_cfg()
    publish(client, cfg, [env(i) for i in range(12)])
    sinks = [MemorySink(), MemorySink()]
    procs = [EventProcessor(client, [s], cfg, consumer=f"c{i}") for i, s in enumerate(sinks)]
    for _ in range(4):
        for p in procs:
            p.pc.batch = 3
            p.run_once()
    a, b = set(sinks[0].ids), set(sinks[1].ids)
    assert len(a) + len(b) == 12 and not a & b and a and b


def test_the_processor_stops_gracefully():
    proc, client, cfg, _ = setup()
    worker = threading.Thread(target=proc.run_forever)
    worker.start()
    publish(client, cfg, [env(1)])
    time.sleep(0.1)
    proc.stop()
    worker.join(timeout=3)
    assert not worker.is_alive() and proc.status()["processed"] == 1


def test_the_processor_survives_an_outage_of_the_stream():
    proc, client, cfg, (sink,) = setup()
    worker = threading.Thread(target=proc.run_forever)
    worker.start()
    client.down = True
    time.sleep(0.2)
    client.down = False
    publish(client, cfg, [env(1)])
    deadline = time.time() + 5
    while not sink.ids and time.time() < deadline:
        time.sleep(0.02)
    proc.stop()
    worker.join(timeout=3)
    assert len(sink.ids) == 1 and proc.status()["stream_errors"] >= 1
