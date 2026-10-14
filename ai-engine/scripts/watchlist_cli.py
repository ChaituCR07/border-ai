import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.db.connection import build_dsn  # noqa: E402
from app.db.migrate import apply_migrations  # noqa: E402
from app.watchlist.config import WatchlistConfig  # noqa: E402
from app.watchlist.csv_io import export_csv, import_csv  # noqa: E402
from app.watchlist.matcher import decide_status, lookup_in_repo, score_for  # noqa: E402
from app.watchlist.models import ENTITY_TYPES, RISK_LEVELS, WatchlistError  # noqa: E402
from app.watchlist.normalize import normalize_plate  # noqa: E402
from app.watchlist.repo import PostgresWatchlistRepo  # noqa: E402


def show(entries):
    print(f"{'id':>4}  {'type':<8}{'identifier':<14}{'risk':<9}{'active':<7}name")
    for e in entries:
        print(f"{e.watchlist_id:>4}  {e.entity_type:<8}{e.normalized_identifier:<14}"
              f"{e.risk_level:<9}{str(e.active):<7}{e.name}")


def main():
    ap = argparse.ArgumentParser(description="Manage the watchlist")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="apply database migrations")
    sub.add_parser("seed-demo", help="import configs/watchlist_demo.csv (synthetic entries)")

    p = sub.add_parser("add")
    p.add_argument("--type", required=True, choices=ENTITY_TYPES)
    p.add_argument("--identifier", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--risk", required=True, choices=RISK_LEVELS)
    p.add_argument("--description", default="")
    p.add_argument("--by", default="cli")

    p = sub.add_parser("list")
    p.add_argument("--all", action="store_true", help="include deactivated entries")
    p.add_argument("--type", choices=ENTITY_TYPES)

    p = sub.add_parser("update")
    p.add_argument("id", type=int)
    p.add_argument("--name")
    p.add_argument("--description")
    p.add_argument("--risk", choices=RISK_LEVELS)
    p.add_argument("--by", default="cli")

    for name in ("remove", "restore"):
        p = sub.add_parser(name)
        p.add_argument("id", type=int)
        p.add_argument("--by", default="cli")
        p.add_argument("--reason", default="")

    p = sub.add_parser("import")
    p.add_argument("csv")
    p.add_argument("--by", default="import")

    p = sub.add_parser("export")
    p.add_argument("csv")
    p.add_argument("--all", action="store_true")

    p = sub.add_parser("check", help="what would happen if this plate were recognized?")
    p.add_argument("plate")
    p.add_argument("--confidence", type=float, default=0.9)

    p = sub.add_parser("hits")
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("audit")
    p.add_argument("--limit", type=int, default=20)

    args = ap.parse_args()
    migrations = config.BASE_DIR / "database" / "migrations"
    if args.cmd == "init":
        print("Applied:", apply_migrations(build_dsn(), migrations) or "nothing (up to date)")
        return

    repo = PostgresWatchlistRepo(build_dsn())
    cfg = WatchlistConfig.from_config(config.load_app_config().get("watchlist"))
    try:
        if args.cmd == "seed-demo":
            added, skipped, errors = import_csv(repo, config.CONFIG_DIR / "watchlist_demo.csv", actor="seed")
            print(f"added {added}, skipped {skipped}, errors {errors}")
        elif args.cmd == "add":
            e = repo.add(args.type, args.identifier, args.name, args.risk, args.description, actor=args.by)
            print(f"added #{e.watchlist_id}: {e.entity_type} {e.normalized_identifier} ({e.risk_level})")
        elif args.cmd == "list":
            show(repo.list_entries([args.type] if args.type else None, active_only=not args.all))
        elif args.cmd == "update":
            e = repo.update(args.id, actor=args.by, name=args.name, description=args.description,
                            risk_level=args.risk)
            show([e])
        elif args.cmd == "remove":
            show([repo.deactivate(args.id, actor=args.by, reason=args.reason)])
        elif args.cmd == "restore":
            show([repo.restore(args.id, actor=args.by)])
        elif args.cmd == "import":
            added, skipped, errors = import_csv(repo, args.csv, actor=args.by)
            print(f"added {added}, skipped {skipped}")
            for msg in errors:
                print("  ", msg)
        elif args.cmd == "export":
            print("exported", export_csv(repo, args.csv, active_only=not args.all), "entries")
        elif args.cmd == "check":
            plate = normalize_plate(args.plate)
            match = lookup_in_repo(repo, plate, cfg)
            if match is None:
                print(f"{plate}: no match")
            else:
                score = score_for(args.confidence, match.quality)
                status = decide_status(match, args.confidence, score, cfg)
                print(f"{plate}: {match.match_type} match with #{match.entry.watchlist_id} "
                      f"({match.entry.risk_level}), distance {match.distance}, score {score}, status {status}")
        elif args.cmd == "hits":
            for h in repo.recent_hits(args.limit):
                print(h)
        elif args.cmd == "audit":
            for a in repo.audit_log(args.limit):
                print(a)
    except WatchlistError as e:
        sys.exit(f"error: {e}")
    finally:
        repo.close()


if __name__ == "__main__":
    main()
