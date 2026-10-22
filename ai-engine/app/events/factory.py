import logging
from typing import Optional

from app.events.config import EventsConfig, mask_url, resolve_redis_url
from app.events.publisher import EventPublisher, StreamTransport
from app.events.streams import RedisStreamClient, StreamUnavailable

log = logging.getLogger("events")


def build_redis_client(cfg: EventsConfig) -> RedisStreamClient:
    return RedisStreamClient.from_url(resolve_redis_url(cfg))


def build_publisher(app_cfg: dict, force: bool = False) -> Optional[EventPublisher]:
    """Build the publisher if events.enabled (or force). Redis does not have to be reachable at startup:
    the publisher buffers and retries."""
    cfg = EventsConfig.from_config(app_cfg.get("events"))
    if not (cfg.enabled or force):
        return None
    client = build_redis_client(cfg)
    try:
        client.length(cfg.stream)
        log.info("Event bus reachable at %s", mask_url(resolve_redis_url(cfg)))
    except StreamUnavailable as e:
        log.warning("Event bus not reachable at startup (%s); events will be buffered and retried", e)
    return EventPublisher(StreamTransport(client, cfg), cfg)
