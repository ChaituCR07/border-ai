import os
from typing import Optional

from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo

from app import config

load_dotenv(config.BASE_DIR / ".env")


def build_dsn(dbname: Optional[str] = None) -> str:
    """Connection string from the POSTGRES_* variables in .env (Day 1)."""
    return make_conninfo(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=dbname or os.getenv("POSTGRES_DB", "borderai"),
        user=os.getenv("POSTGRES_USER", "borderai"),
        password=os.getenv("POSTGRES_PASSWORD") or None,
    )


def admin_conninfo() -> str:
    """Connection to the maintenance database (used by tests to create a temporary database)."""
    return build_dsn("postgres")
