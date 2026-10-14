import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.db.connection import build_dsn  # noqa: E402
from app.db.migrate import apply_migrations  # noqa: E402

if __name__ == "__main__":
    applied = apply_migrations(build_dsn(), config.BASE_DIR / "database" / "migrations")
    print("Applied:", applied if applied else "nothing (already up to date)")
