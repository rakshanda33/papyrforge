"""SQLite connection and schema setup for persisted job records."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.settings import DATABASE_PATH


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection and commit or roll back its transaction."""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=5)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the jobs table if this is the first application run."""
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                upload_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('queued', 'processing', 'completed', 'failed')
                ),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error_message TEXT
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS jobs_by_status_and_creation "
            "ON jobs (status, created_at)"
        )
