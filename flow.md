# PDFForge execution flow

This document describes the current code path. The upload endpoint only checks a PDF signature and stores bytes; it does not fully parse or process a PDF.

## Application startup

1. The ASGI server imports `app.main` and uses its `app` object.
2. `app.main` imports `FastAPI` and the router from `app.api.uploads`.
3. Importing `app.api.uploads` also imports the validation and storage functions. Storage imports settings from `app.settings`.
4. `app.main` creates `FastAPI(title="PDFForge", version="0.1.0")` and registers the upload router with `app.include_router(uploads_router)`.
5. The app exposes `POST /uploads` from the router and `GET /health` from `app.main`.

## Upload flow diagram

```text
Browser
  │ multipart POST /uploads with file
  ▼
FastAPI app (`app/main.py`)
  │ registered upload router
  ▼
`upload_pdf(file)` (`app/api/uploads.py`)
  ├─ `read_and_validate_pdf_header(file)` (`app/services/validation.py`)
  │    └─ read up to 1,024 bytes → seek back to position 0
  ├─ `save_pdf(file)` (`app/storage/local.py`)
  │    ├─ create upload directory
  │    ├─ stream chunks to temporary file and count bytes
  │    └─ rename completed file; return UUID and byte count
  ├─ finally: close upload
  └─ return JSON metadata with HTTP 201
```

## Numbered successful request sequence

1. The browser sends a multipart `POST /uploads` request. FastAPI parses the multipart request and supplies an `UploadFile` named `file` to `upload_pdf()`.
2. `upload_pdf()` calls `read_and_validate_pdf_header(file)`.
3. `read_and_validate_pdf_header()` reads up to `HEADER_SEARCH_BYTES` (1,024) and then calls `upload.seek(0)`. The rewind is necessary because the next function must save the file starting at byte zero.
4. If the bytes contain `PDF_HEADER` (`b"%PDF-"`), validation returns normally. This is only a quick signature check, not full PDF parsing or a safety guarantee. The request Content-Type is not used as proof of format.
5. `upload_pdf()` calls `save_pdf(file)`. That function reads `UPLOAD_DIR`, `MAX_UPLOAD_BYTES`, and `UPLOAD_CHUNK_BYTES` from `app.settings`.
6. `save_pdf()` creates `UPLOAD_DIR` if needed, generates a UUID, and forms a temporary path (`.<uuid>.uploading`) and final path (`<uuid>.pdf`).
7. It opens the temporary path with `"xb"` (create exclusively for writing). It repeatedly reads up to `UPLOAD_CHUNK_BYTES` (1 MiB), adds each chunk's length to `total_bytes`, checks whether the total exceeds `MAX_UPLOAD_BYTES` (25 MiB by default), and writes allowed chunks.
8. If the loop completes with zero bytes, `save_pdf()` raises HTTP 400. Otherwise it renames the temporary file to the final path and returns `(upload_id, total_bytes)`.
9. `upload_pdf()`'s `finally` block closes `file`, regardless of success or failure. After a successful save, the endpoint returns a JSON dictionary containing the UUID, original client filename (or `upload.pdf` fallback), byte count, and message. FastAPI sends it with HTTP 201 Created.

## Error paths and cleanup

- **Empty upload:** The header function reads no bytes and raises HTTP 400. The route's `finally` block still closes the upload. The later empty check in `save_pdf()` is normally not reached through this route.
- **No PDF signature in first 1,024 bytes:** Validation raises HTTP 415. Storage is not called; the route closes the upload in `finally`.
- **Upload exceeds limit:** `save_pdf()` raises HTTP 413 when cumulative bytes read exceed `MAX_UPLOAD_BYTES` (the chunk that crosses the limit is counted but not written). Its `except` block tries to delete the temporary path and re-raises the error. The route then closes the upload in `finally`.
- **Other exception while saving:** `save_pdf()` also tries to delete the temporary file and re-raises. The route closes the upload. An unhandled exception is handled by FastAPI as a server error.
- **Directory creation failure:** `UPLOAD_DIR.mkdir(...)` happens before `save_pdf()`'s `try` block, so this failure is not handled by its temporary-file cleanup block. The route still closes the upload.
- **Successful storage:** `temporary.replace(destination)` runs only after all chunks are written and the file is non-empty. If an exception occurs inside the `try`, the code attempts to unlink the temporary file.

## Health route

`GET /health` is defined directly in `app/main.py`. FastAPI calls the async `health()` function, which returns `{"status": "ok"}`; FastAPI serializes that dictionary as JSON. It does not inspect upload storage or the health of other services.

## Future maintenance

Update this file whenever an approved code change alters startup, request flow, function calls, data flow, cleanup, or error handling.
