"""Validation rules for uploaded PDF files."""

from fastapi import HTTPException, UploadFile, status


PDF_HEADER = b"%PDF-"
HEADER_SEARCH_BYTES = 1024


async def read_and_validate_pdf_header(upload: UploadFile) -> None:
    """Read the initial bytes and check for a PDF signature.

    The signature is a quick format check, not a complete PDF parser or safety
    check. A processing library must still open the file before using it.
    """
    header = await upload.read(HEADER_SEARCH_BYTES)
    await upload.seek(0)

    if not header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if PDF_HEADER not in header:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file does not appear to be a PDF.",
        )
