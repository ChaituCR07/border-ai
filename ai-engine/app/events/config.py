import os
import re
from dataclasses import dataclass, field, fields, replace
from typing import List
from urllib.parse import quote

from dotenv import load_dotenv

from app import config

_CREDENTIALS = re.compile(r"(://)[^/@\s]*@")


def mask_url(url: str) -> str:
    """Hide credentials before a URL is logged."""
    return _CREDENTIALS.sub(r"\1***@", url)


def _build(cls, data):
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in (data or {}).items() if k in known})


@dataclass
class ProcessorConfig:
    group: str = "processor"
    consumer: str = "processor-1"
    start: str = "0"
    block_ms: int = 1000
    batch: int = 50
    reclaim_idle_ms: int = 30000
    reclaim_every_s: float = 5.0
    max_deliveries: int = 5
    dedupe_cache: int = 20000
    dead_maxlen: int = 10000

    def __post_init__(self):
        if self.start not in ("0", "$"):
            raise ValueError("processor.start must be '0' or '$'")
        if self.batch < 1 or self.max_deliveries < 1 or self.dedupe_cache < 1:
            raise ValueError("processor.batch, max_deliveries, and dedupe_cache must be >= 1")


@dataclass
class EventsConfig:
    enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"
    stream: str = "surveillance.events"
    alerts_stream: str = "surveillance.alerts"
    dead_stream: str = "surveillance.events.dead"
    alert_types: List[str] = field(default_factory=lambda: ["THREAT_ALERT"])
    maxlen: int = 100000
    alerts_maxlen: int = 10000
    batch_size: int = 100
    flush_ms: int = 50
    buffer_high: int = 5000
    buffer_low: int = 20000
    high_priority_types: List[str] = field(default_factory=lambda: [
        "THREAT_ALERT", "WATCHLIST_MATCH", "ZONE_VIOLATION", "DIRECTION_VIOLATION", "LOITERING_VIOLATION",
        "AFTER_HOURS_ACTIVITY", "UNAUTHORIZED_VEHICLE_AFTER_HOURS"])
    retry_initial_s: float = 0.5
    retry_max_s: float = 10.0
    shutdown_timeout_s: float = 10.0
    processor: ProcessorConfig = field(default_factory=ProcessorConfig)

    def __post_init__(self):
        if len({self.stream, self.alerts_stream, self.dead_stream}) != 3:
            raise ValueError("stream, alerts_stream, and dead_stream must be different")
        if self.batch_size < 1 or self.buffer_high < 1 or self.buffer_low < 1 or self.maxlen < 1:
            raise ValueError("batch_size, buffers, and maxlen must be >= 1")
        if self.retry_initial_s <= 0 or self.retry_max_s < self.retry_initial_s:
            raise ValueError("retry_initial_s must be > 0 and <= retry_max_s")

    @classmethod
    def from_config(cls, cfg: dict) -> "EventsConfig":
        cfg = dict(cfg or {})
        proc = _build(ProcessorConfig, cfg.pop("processor", None))
        return replace(_build(cls, cfg), processor=proc)


def resolve_redis_url(cfg: EventsConfig) -> str:
    """REDIS_URL, else REDIS_HOST/PORT/PASSWORD from .env (Day 1), else the configured URL."""
    load_dotenv(config.BASE_DIR / ".env")
    url = os.getenv("REDIS_URL")
    if url:
        return url
    host = os.getenv("REDIS_HOST")
    if host:
        password = os.getenv("REDIS_PASSWORD", "")
        auth = f":{quote(password, safe='')}@" if password else ""
        return f"redis://{auth}{host}:{os.getenv('REDIS_PORT', '6379')}/0"
    return cfg.redis_url
