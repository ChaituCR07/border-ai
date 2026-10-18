import psycopg
import pytest

from app import config
from app.db.migrate import apply_migrations

pytestmark = pytest.mark.db


def test_migrations_are_idempotent(pg_dsn):
    assert apply_migrations(pg_dsn, config.BASE_DIR / "database" / "migrations") == []
    with psycopg.connect(pg_dsn) as conn:
        for table in ("watchlist", "watchlist_audit", "watchlist_hits", "schema_migrations"):
            assert conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()[0] is not None
        versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert "001_watchlist.sql" in versions


def test_check_constraints_reject_bad_values_even_without_the_python_validation(pg_repo):
    with pg_repo.pool.connection() as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO watchlist (entity_type, identifier, normalized_identifier, name, risk_level) "
                         "VALUES ('VEHICLE', 'X', 'X', 'n', 'SEVERE')")


def test_partial_unique_index_only_covers_active_rows(pg_repo):
    a = pg_repo.add("VEHICLE", "KA01AB1234", "A", "HIGH")
    pg_repo.deactivate(a.watchlist_id)
    with pg_repo.pool.connection() as conn:                 # direct inserts: one inactive + one active is fine
        conn.execute("INSERT INTO watchlist (entity_type, identifier, normalized_identifier, name, risk_level) "
                     "VALUES ('VEHICLE', 'KA01AB1234', 'KA01AB1234', 'B', 'LOW')")
    with pytest.raises(Exception):                          # a second ACTIVE duplicate is refused
        with pg_repo.pool.connection() as conn:
            conn.execute("INSERT INTO watchlist (entity_type, identifier, normalized_identifier, name, risk_level) "
                         "VALUES ('VEHICLE', 'ka01ab1234', 'KA01AB1234', 'C', 'LOW')")


def test_the_repository_reports_an_unreachable_database():
    from app.db.connection import build_dsn
    from app.watchlist.models import RepoUnavailable
    from app.watchlist.repo import PostgresWatchlistRepo
    repo = PostgresWatchlistRepo(build_dsn("borderai") + " port=1", timeout=0.5)     # nothing listens on port 1
    try:
        with pytest.raises(RepoUnavailable):
            repo.ping()
    finally:
        repo.close()


def test_migration_002_is_applied_and_enforces_embedding_rules(pg_repo):
    import psycopg
    with pg_repo.pool.connection() as conn:
        assert conn.execute("SELECT 1 FROM schema_migrations WHERE version = '002_face_embeddings.sql'").fetchone()
    with pytest.raises(psycopg.errors.CheckViolation):          # a FACE row without an embedding is refused
        with pg_repo.pool.connection() as conn:
            conn.execute("INSERT INTO watchlist (entity_type, identifier, normalized_identifier, name, risk_level) "
                         "VALUES ('FACE', 's', 's', 'n', 'LOW')")
    with pytest.raises(psycopg.errors.CheckViolation):          # a plate row with an embedding is refused
        with pg_repo.pool.connection() as conn:
            conn.execute("INSERT INTO watchlist (entity_type, identifier, normalized_identifier, name, risk_level, embedding) "
                         "VALUES ('VEHICLE', 'KA01AB1234', 'KA01AB1234', 'n', 'LOW', '\\x00')")
