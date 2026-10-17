"""Create, read, and update persisted processing jobs."""

from datetime import datetime, timezone
from uuid import uuid4

from app.db import database_connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(upload_id: str) -> dict[str, str | None]:
    """Save a new job in the queued state and return its public fields."""
    job = {
        "job_id": str(uuid4()),
        "upload_id": upload_id,
        "status": "queued",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "error_message": None,
    }

    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO jobs (job_id, upload_id, status, created_at, updated_at, error_message)
            VALUES (:job_id, :upload_id, :status, :created_at, :updated_at, :error_message)
            """,
            job,
        )

    return job


def get_job(job_id: str) -> dict[str, str | None] | None:
    """Return one job as a dictionary, or None if it does not exist."""
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT job_id, upload_id, status, created_at, updated_at, error_message
            FROM jobs WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

    return dict(row) if row is not None else None


def claim_next_job() -> dict[str, str | None] | None:
    """Atomically move the oldest queued job to processing."""
    with database_connection() as connection:
        # Reserve the write transaction so two workers cannot claim the same job.
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT job_id, upload_id, status, created_at, updated_at, error_message
            FROM jobs WHERE status = 'queued'
            ORDER BY created_at, job_id LIMIT 1
            """
        ).fetchone()

        if row is None:
            return None

        job = dict(row)
        updated_at = _utc_now()
        connection.execute(
            "UPDATE jobs SET status = 'processing', updated_at = ? WHERE job_id = ?",
            (updated_at, job["job_id"]),
        )
        job["status"] = "processing"
        job["updated_at"] = updated_at

    return job


def finish_job(job_id: str, status: str, error_message: str | None = None) -> None:
    """Save a job's final status and optional safe error message."""
    if status not in {"completed", "failed"}:
        raise ValueError("A job can only finish as completed or failed.")

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE jobs SET status = ?, updated_at = ?, error_message = ?
            WHERE job_id = ? AND status = 'processing'
            """,
            (status, _utc_now(), error_message, job_id),
        )
