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


@pytest.fixture(scope="session")
def redis_url():
    redis = pytest.importorskip("redis")
    from app.events.config import EventsConfig, resolve_redis_url
    url = resolve_redis_url(EventsConfig())
    try:
        redis.Redis.from_url(url, socket_connect_timeout=2).ping()
    except Exception as e:                                                    # noqa: BLE001
        pytest.skip(f"Redis not reachable ({type(e).__name__}); start it with: docker compose up -d redis")
    return url


@pytest.fixture
def stream_name():
    return f"test.{uuid.uuid4().hex[:10]}"


@pytest.fixture(params=["memory", pytest.param("redis", marks=pytest.mark.redis)])
def stream_client(request, stream_name):
    """Every test that uses `stream_client` runs against BOTH implementations."""
    from app.events.streams import InMemoryStreamClient, RedisStreamClient
    if request.param == "memory":
        client = InMemoryStreamClient()
    else:
        client = RedisStreamClient.from_url(request.getfixturevalue("redis_url"))
    yield client
    for name in (stream_name, f"{stream_name}.dead", f"{stream_name}.alerts"):
        try:
            client.delete(name)
        except Exception:                                                     # noqa: BLE001
            pass


@pytest.fixture(params=["memory", pytest.param("postgres", marks=pytest.mark.db)])
def event_repo(request):
    """Every test that uses `event_repo` runs against BOTH implementations."""
    from app.db.events_repo import InMemoryEventRepository, PostgresEventRepository
    if request.param == "memory":
        yield InMemoryEventRepository()
        return
    repo = PostgresEventRepository(request.getfixturevalue("pg_dsn"))
    with repo._conn() as conn:
        conn.execute("TRUNCATE alert_history, alerts, vehicles, detections, events, cameras RESTART IDENTITY CASCADE")
    yield repo
    repo.close()
