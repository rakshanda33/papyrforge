"""Job status endpoint."""

from fastapi import APIRouter, HTTPException

from app.repositories.jobs import get_job


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def read_job(job_id: str) -> dict[str, str | None]:
    """Return the saved status for one job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
