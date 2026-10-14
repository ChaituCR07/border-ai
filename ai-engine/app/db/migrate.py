from pathlib import Path
from typing import List

import psycopg


def apply_migrations(dsn: str, migrations_dir: Path) -> List[str]:
    """Apply every *.sql file not yet recorded in schema_migrations. Returns the names applied."""
    applied_now: List[str] = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                            version    TEXT PRIMARY KEY,
                            applied_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(Path(migrations_dir).glob("*.sql")):
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now
