import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.events_repo import PostgresEventRepository  # noqa: E402
from app.watchlist.dsn import build_dsn  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Delete old events and alerts by policy")
    ap.add_argument("--events-days", type=int, required=True, help="keep events this many days")
    ap.add_argument("--alerts-days", type=int, required=True, help="keep alerts this many days (>= events-days)")
    ap.add_argument("--yes", action="store_true", help="actually delete (the default is a report only)")
    args = ap.parse_args()
    if args.alerts_days < args.events_days:
        sys.exit("alerts-days must be >= events-days (an alert's event is kept while the alert is kept)")

    now = datetime.now(timezone.utc)
    events_before, alerts_before = now - timedelta(days=args.events_days), now - timedelta(days=args.alerts_days)
    repo = PostgresEventRepository(build_dsn())
    print("before:", repo.stats())
    if not args.yes:
        print(f"dry run: would delete alerts older than {alerts_before:%Y-%m-%d} and events older than "
              f"{events_before:%Y-%m-%d} that no remaining alert needs. Use --yes to delete.")
        return
    print("deleted:", repo.purge(events_before, alerts_before))
    print("after:", repo.stats())
    print("Remember: evidence snapshot files under outputs/runs/ are not deleted by this tool.")


if __name__ == "__main__":
    main()
