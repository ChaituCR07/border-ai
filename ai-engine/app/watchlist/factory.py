import logging
from typing import Optional

from app import config
from app.db.connection import build_dsn
from app.watchlist.config import WatchlistConfig
from app.watchlist.csv_io import import_csv
from app.watchlist.models import RepoUnavailable
from app.watchlist.repo import InMemoryWatchlistRepo, PostgresWatchlistRepo
from app.watchlist.service import WatchlistService

log = logging.getLogger("watchlist")


def build_watchlist(app_cfg: dict) -> Optional[WatchlistService]:
    cfg = WatchlistConfig.from_config(app_cfg.get("watchlist"))
    if not cfg.enabled:
        return None

    if cfg.backend == "memory":
        repo = InMemoryWatchlistRepo()
        if cfg.seed_csv:
            added, skipped, errors = import_csv(repo, config.BASE_DIR / cfg.seed_csv, actor="seed")
            log.info("Seeded in-memory watchlist: %d added, %d skipped", added, skipped)
    else:
        repo = PostgresWatchlistRepo(build_dsn())
        try:
            repo.ping()
        except RepoUnavailable as e:
            if cfg.require_db:
                raise RuntimeError(f"Watchlist database unreachable and require_db is true: {e}") from e
            log.error("Watchlist database unreachable (%s). Running WITHOUT a watchlist until it "
                      "returns; set watchlist.require_db: true to refuse to start instead.", e)
    return WatchlistService(repo, cfg)
