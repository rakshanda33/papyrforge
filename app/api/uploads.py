"""Upload endpoint."""

from fastapi import APIRouter, File, UploadFile, status

from app.repositories.jobs import create_job
from app.services.validation import read_and_validate_pdf_header
from app.storage.local import save_pdf


router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, str | int]:
    """Validate and privately store a PDF, returning its generated identifier."""
    try:
        await read_and_validate_pdf_header(file)

        # Content-Type is supplied by the client, so it is informational only.
        # The PDF signature and enforced byte limit are the checks used here.
        upload_id, size_bytes = await save_pdf(file)
    finally:
        await file.close()

    job = create_job(upload_id)

    return {
        "upload_id": upload_id,
        "job_id": job["job_id"],
        "status": job["status"],
        "original_filename": file.filename or "upload.pdf",
        "size_bytes": size_bytes,
        "message": "PDF uploaded and queued for processing.",
    }
