import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.events_repo import PostgresEventRepository  # noqa: E402
from app.watchlist.dsn import build_dsn  # noqa: E402

if __name__ == "__main__":
    repo = PostgresEventRepository(build_dsn())
    for key, value in repo.stats().items():
        print(f"{key:<16}{value}")
    print("\nalerts by priority (open / new / total):")
    for priority, c in repo.alert_counts().items():
        print(f"  {priority:<10}{c['open']:>5} / {c['new']:>5} / {c['total']:>5}")
    repo.close()
