import logging
import os
import signal
import sys
import time
from pathlib import Path

# Add project roots to sys.path so engine and ai-engine modules resolve cleanly
ROOT_DIR = Path(__file__).resolve().parents[2]
AI_ENGINE_DIR = ROOT_DIR / "ai-engine"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(AI_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_DIR))

from app import config
from app.db.connection import build_dsn
from app.db.events_repo import PostgresEventRepository
from app.events.config import EventsConfig
from app.events.db_sink import PostgresEventSink
from app.events.factory import build_redis_client
from app.events.processor import ConsoleAlertSink, EventProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sink.postgres")


def main():
    logger.info("Initializing Border-AI Postgres Event Sink...")
    app_cfg = config.load_app_config()
    cfg = EventsConfig.from_config(app_cfg.get("events"))

    dsn = build_dsn()
    repo = PostgresEventRepository(dsn)
    sinks = [ConsoleAlertSink(), PostgresEventSink(repo)]

    from app.events.streams import StreamUnavailable
    while True:
        try:
            proc = EventProcessor(build_redis_client(cfg), sinks, cfg, consumer="sink-postgres")
            break
        except StreamUnavailable as e:
            logger.warning("Event bus not reachable (%s); retrying in 2s...", e)
            time.sleep(2)
        except Exception as e:
            logger.warning("Waiting for storage dependencies (%s); retrying in 3s...", e)
            time.sleep(3)

    running = True

    def stop_signal(*_):
        nonlocal running
        running = False
        proc.stop()

    signal.signal(signal.SIGINT, stop_signal)
    signal.signal(signal.SIGTERM, stop_signal)

    logger.info("Processor %s consuming from %s to Postgres", proc.consumer, cfg.stream)
    proc.run_forever()


if __name__ == "__main__":
    main()
