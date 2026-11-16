import os
from typing import Optional

from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo

from app import config

load_dotenv(config.BASE_DIR / ".env")


def build_dsn(dbname: Optional[str] = None) -> str:
    """Connection string from the DB_* or POSTGRES_* environment variables."""
    host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT", "5432")
    db = dbname or os.getenv("DB_NAME") or os.getenv("POSTGRES_DB", "borderai")
    user = os.getenv("DB_USER") or os.getenv("POSTGRES_USER", "borderai")
    password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or None

    if not password:
        password_file = os.getenv("DB_PASSWORD_FILE")
        if password_file and os.path.exists(password_file):
            try:
                with open(password_file, "r", encoding="utf-8") as f:
                    password = f.read().strip()
            except Exception:
                pass

    return make_conninfo(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=password,
    )


def admin_conninfo() -> str:
    """Connection to the maintenance database (used by tests to create a temporary database)."""
    return build_dsn("postgres")
