import uuid

import pytest

from app.watchlist.repo import InMemoryWatchlistRepo


@pytest.fixture(scope="session")
def pg_dsn():
    """A temporary PostgreSQL database with the migrations applied. Skips if PostgreSQL is not running."""
    psycopg = pytest.importorskip("psycopg")
    from app import config
    from app.db.connection import admin_conninfo, build_dsn
    from app.db.migrate import apply_migrations

    try:
        admin = psycopg.connect(admin_conninfo(), autocommit=True, connect_timeout=2)
    except Exception as e:
        pytest.skip(f"PostgreSQL not reachable ({type(e).__name__}); start it with: docker compose up -d postgres")

    name = f"borderai_test_{uuid.uuid4().hex[:8]}"
    admin.execute(f'CREATE DATABASE "{name}"')
    dsn = build_dsn(name)
    apply_migrations(dsn, config.BASE_DIR / "database" / "migrations")
    yield dsn
    admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                  "WHERE datname = %s AND pid <> pg_backend_pid()", (name,))
    admin.execute(f'DROP DATABASE IF EXISTS "{name}"')
    admin.close()


@pytest.fixture
def pg_repo(pg_dsn):
    from app.watchlist.repo import PostgresWatchlistRepo
    repo = PostgresWatchlistRepo(pg_dsn)
    with repo.pool.connection() as conn:
        conn.execute("TRUNCATE watchlist, watchlist_audit, watchlist_hits RESTART IDENTITY CASCADE")
    yield repo
    repo.close()


@pytest.fixture(params=["memory", pytest.param("postgres", marks=pytest.mark.db)])
def repo(request):
    """Every test that uses `repo` runs against BOTH repositories."""
    if request.param == "memory":
        yield InMemoryWatchlistRepo()
    else:
        yield request.getfixturevalue("pg_repo")
