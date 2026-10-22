import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.events.config import EventsConfig  # noqa: E402
from app.events.factory import build_redis_client  # noqa: E402
from app.events.stats import collect_stats, format_stats  # noqa: E402

if __name__ == "__main__":
    cfg = EventsConfig.from_config(config.load_app_config().get("events"))
    print(format_stats(collect_stats(build_redis_client(cfg), cfg)))
    print("\nlag = entries the group has not read yet; pending = read but not acknowledged; "
          "a growing dead stream means messages are failing.")
