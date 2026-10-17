"""Private local storage for uploaded source PDFs."""

from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.settings import MAX_UPLOAD_BYTES, UPLOAD_CHUNK_BYTES, UPLOAD_DIR


async def save_pdf(upload: UploadFile) -> tuple[str, int]:
    """Stream an upload to a generated path, enforcing the byte limit."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    upload_id = str(uuid4())
    destination = UPLOAD_DIR / f"{upload_id}.pdf"
    temporary = UPLOAD_DIR / f".{upload_id}.uploading"
    total_bytes = 0

    try:
        with temporary.open("xb") as output:
            while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {MAX_UPLOAD_BYTES}-byte upload limit.",
                    )
                output.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty.",
            )

        temporary.replace(destination)
        return upload_id, total_bytes
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def upload_exists(upload_id: str) -> bool:
    """Check for a stored upload using its UUID, not a client-provided path."""
    try:
        normalized_id = UUID(upload_id)
    except ValueError:
        return False

    return (UPLOAD_DIR / f"{normalized_id}.pdf").is_file()
