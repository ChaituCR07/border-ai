import time

from app.events.config import EventsConfig, ProcessorConfig
from app.events.envelope import envelope_from_event
from behaviour_helpers import obs


def make_events_cfg(**kw) -> EventsConfig:
    proc = kw.pop("processor", ProcessorConfig(block_ms=10, batch=20, reclaim_idle_ms=50, reclaim_every_s=0.0,
                                                max_deliveries=3, dedupe_cache=1000))
    base = dict(enabled=True, batch_size=10, flush_ms=5, buffer_high=50, buffer_low=100, retry_initial_s=0.01,
                retry_max_s=0.05, shutdown_timeout_s=2.0, processor=proc)
    base.update(kw)
    return EventsConfig(**base)


def ev(i, type_="ZONE_VIOLATION", cam="CAM_1", track=1, severity=None):
    details = {"severity": severity} if severity else {}
    return obs(type_, 1_000_000.0 + i, track=track, cam=cam, rule_id=f"R{i}", rule_kind="behaviour", details=details)


def env(i, **kw):
    return envelope_from_event(ev(i, **kw), run_id="RUN1")


def wait_until(condition, timeout=5.0, interval=0.01):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(interval)
    return False


def drain(processor, rounds=50):
    """Run the processor until two consecutive cycles find nothing to do."""
    quiet = 0
    for _ in range(rounds):
        quiet = quiet + 1 if processor.run_once() == 0 else 0
        if quiet >= 2:
            return
        time.sleep(0.002)
