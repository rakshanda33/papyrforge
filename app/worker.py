"""Small SQLite-polling worker for demonstrating the job lifecycle."""

import time

from app.db import initialize_database
from app.repositories.jobs import claim_next_job, finish_job
from app.settings import WORKER_POLL_INTERVAL_SECONDS
from app.storage.local import upload_exists


def process_next_job() -> bool:
    """Process one queued job; return False when the queue is empty.

    This milestone only confirms that the saved upload still exists. PDF
    analysis will be added in a later milestone.
    """
    job = claim_next_job()
    if job is None:
        return False

    try:
        if not upload_exists(job["upload_id"] or ""):
            finish_job(job["job_id"] or "", "failed", "Saved upload was not found.")
        else:
            finish_job(job["job_id"] or "", "completed")
    except OSError:
        finish_job(job["job_id"] or "", "failed", "Could not access the saved upload.")

    return True


def run_worker() -> None:
    """Initialize SQLite and keep checking for queued jobs."""
    initialize_database()
    print("PDFForge worker is running. Press Ctrl+C to stop.")

    while True:
        if not process_next_job():
            time.sleep(WORKER_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_worker()
