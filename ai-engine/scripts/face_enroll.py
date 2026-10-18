import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.db.connection import build_dsn  # noqa: E402
from app.identity.config import IdentityConfig  # noqa: E402
from app.identity.enroll import enroll_subject  # noqa: E402
from app.identity.factory import build_face_engine  # noqa: E402
from app.watchlist.models import RISK_LEVELS, WatchlistError  # noqa: E402
from app.watchlist.repo import PostgresWatchlistRepo  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Enrol ONE consenting person from several photos")
    ap.add_argument("--folder", required=True, help="folder with photos of that one person")
    ap.add_argument("--identifier", required=True, help="a neutral label, e.g. subject-001")
    ap.add_argument("--name", required=True)
    ap.add_argument("--risk", default="LOW", choices=RISK_LEVELS)
    ap.add_argument("--by", default="cli")
    ap.add_argument("--consent-confirmed", action="store_true",
                    help="REQUIRED: you confirm this person agreed to be enrolled")
    args = ap.parse_args()

    app_cfg = config.load_app_config()
    cfg = IdentityConfig.from_config(app_cfg.get("identity"))
    engine = build_face_engine(cfg.face, app_cfg.get("model", {}).get("device", "auto"))
    if engine is None:
        sys.exit("No face engine available")

    images = [cv2.imread(str(p)) for p in sorted(Path(args.folder).iterdir())
              if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    images = [i for i in images if i is not None]
    repo = PostgresWatchlistRepo(build_dsn())
    try:
        result = enroll_subject(repo, engine, images, args.identifier, args.name, args.risk, cfg.face,
                                consent_confirmed=args.consent_confirmed, actor=args.by)
        print(f"enrolled #{result.entry.watchlist_id} ({args.identifier}) from {result.used} photos, "
              f"consistency {result.consistency:.2f}, model {engine.model_name}")
        for s in result.skipped:
            print("  skipped", s)
    except WatchlistError as e:
        sys.exit(f"error: {e}")
    finally:
        repo.close()


if __name__ == "__main__":
    main()
