# PDFForge decisions

This file records meaningful technical choices made for the current implementation. “Implemented” means the choice is present in source code; it does not mean tests verified it.

## 2026-10-15 — Use Python and FastAPI for the backend

- **Decision:** Use Python with FastAPI for the API.
- **Why:** PDFForge is a backend-learning project, and the approved project direction selected Python for its PDF and image-processing ecosystem and FastAPI for building a small typed HTTP API.
- **Trade-off or limitation:** The dependencies are version-ranged in `requirements.txt`, not locked to exact versions. Async endpoints do not by themselves make CPU-heavy PDF work faster; processing will need a suitable execution design in a later milestone.
- **Files affected:** `requirements.txt`, `app/main.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Keep app setup separate from upload routes

- **Decision:** Create the FastAPI application in `app/main.py` and define upload endpoints in `app/api/uploads.py`.
- **Why:** The app entry point can register routes while route code remains in a focused module.
- **Trade-off or limitation:** This is a small separation for the current app; more modules add navigation overhead while there are few routes.
- **Files affected:** `app/main.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Group upload endpoints with `APIRouter`

- **Decision:** Define the upload endpoint on an `APIRouter` with the `/uploads` prefix and register it from `main.py`.
- **Why:** A router groups related endpoints and lets the application include them as a unit.
- **Trade-off or limitation:** The router must be included by the app or its routes will not be available.
- **Files affected:** `app/api/uploads.py`, `app/main.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Receive uploads as `UploadFile` using `File(...)`

- **Decision:** Declare the endpoint parameter as `file: UploadFile = File(...)`.
- **Why:** `File(...)` tells FastAPI that a required file comes from a multipart request; `UploadFile` provides file-like read, seek, and close operations suitable for chunked handling.
- **Trade-off or limitation:** The request must use multipart form upload. The client-provided filename and content type are not trustworthy evidence of the file's actual format.
- **Files affected:** `app/api/uploads.py`, `app/services/validation.py`, `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Check the PDF signature before storing

- **Decision:** Search the first 1,024 bytes for the byte signature `%PDF-` before calling storage.
- **Why:** A filename extension can be misleading, so the code makes a basic check against file contents.
- **Trade-off or limitation:** This is only a signature check. It does not parse the entire PDF or prove that the file is safe or usable. The request's MIME type is informational and is not validated.
- **Files affected:** `app/services/validation.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Rewind the upload after inspecting its header

- **Decision:** Call `upload.seek(0)` after reading the header.
- **Why:** Reading advances the stream position. Rewinding lets storage read and save the complete file from its first byte.
- **Trade-off or limitation:** The current flow relies on the upload object supporting seeking, as FastAPI's `UploadFile` does.
- **Files affected:** `app/services/validation.py`, `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Enforce an upload byte limit while writing chunks

- **Decision:** Save the file in 1 MiB chunks and reject it once its cumulative size exceeds 25 MiB by default.
- **Why:** Chunked reads avoid loading the whole upload into application memory at once, and the running byte count enforces a limit even when request metadata is absent or inaccurate.
- **Trade-off or limitation:** The default limit may need adjustment for real workloads. The chunk size is fixed in code; the maximum file size can be changed with `PDFFORGE_MAX_UPLOAD_BYTES`.
- **Files affected:** `app/storage/local.py`, `app/settings.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Use generated UUIDs for stored filenames

- **Decision:** Name each stored PDF with a generated UUID rather than using the uploaded filename as its storage path.
- **Why:** The client filename should not control the filesystem path, which avoids path manipulation and accidental name collisions in this storage scheme.
- **Trade-off or limitation:** The original filename is returned as metadata, but there is not yet a database mapping or download endpoint. A UUID is an identifier, not an access-control mechanism.
- **Files affected:** `app/storage/local.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Write to a temporary file, then rename on success

- **Decision:** Write to a hidden `.uploading` file opened with exclusive-create mode (`"xb"`), then rename it to the final `.pdf` path after writing succeeds.
- **Why:** The final filename is only used after the complete write succeeds; exclusive creation avoids opening an already existing temporary filename.
- **Trade-off or limitation:** This prevents incomplete writes from appearing under the final filename, but it is not a complete durability guarantee for power loss or filesystem failure. If a write fails, the code attempts to remove the temporary file.
- **Files affected:** `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Reject empty uploads

- **Decision:** Reject an empty file with HTTP 400.
- **Why:** An empty file cannot be a useful PDF input for later processing.
- **Trade-off or limitation:** The route's header check rejects an empty upload before `save_pdf()` is called. `save_pdf()` also contains an empty-file check, which protects direct use of that function but is normally unreachable through this route.
- **Files affected:** `app/services/validation.py`, `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Close the upload in a `finally` block

- **Decision:** Close the `UploadFile` in `upload_pdf()`'s `finally` block.
- **Why:** The upload should be closed whether validation and saving succeed or raise an error, releasing its temporary resources.
- **Trade-off or limitation:** Cleanup is tied to the route; any future code path that handles uploads outside this route must also close them.
- **Files affected:** `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Return upload metadata with HTTP 201

- **Decision:** Return JSON containing `upload_id`, `original_filename`, `size_bytes`, and a message, with HTTP 201 Created.
- **Why:** The client receives an identifier for the saved upload and basic information about what the server accepted. HTTP 201 communicates that the upload resource was created.
- **Trade-off or limitation:** The ID is not yet backed by a job record, and the project has no download route. `original_filename` is client-provided display metadata, not a storage path.
- **Files affected:** `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Centralize upload settings

- **Decision:** Keep the upload directory, byte limit, and chunk size in `app/settings.py`.
- **Why:** Storage behavior can use one set of named values instead of embedding these values throughout the upload logic.
- **Trade-off or limitation:** `UPLOAD_DIR` and `MAX_UPLOAD_BYTES` can be set through environment variables; `UPLOAD_CHUNK_BYTES` is currently fixed at 1 MiB. The configured path is local filesystem storage.
- **Files affected:** `app/settings.py`, `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## Future maintenance

Update this file whenever a meaningful technical decision is proposed, approved, implemented, or rejected. Keep its status accurate; do not mark a choice verified unless there is evidence from actual verification.
