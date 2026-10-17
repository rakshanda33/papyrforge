# PDFForge decisions

This file records meaningful technical choices. **Implemented** means the choice is present in the source; it does not mean tests verified it.

## 2026-10-15 — Use Python and FastAPI for the backend

- **Decision:** Use Python with FastAPI for the API.
- **Why:** PDFForge is a backend-learning project. Python has a useful PDF and image-processing ecosystem, and FastAPI provides a small typed HTTP API.
- **Trade-off or limitation:** Dependencies are version-ranged, not locked. Async endpoints do not make CPU-heavy PDF work faster by themselves.
- **Files affected:** `requirements.txt`, `app/main.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Separate application setup from upload routes

- **Decision:** Create the FastAPI app in `app/main.py` and define upload routes in `app/api/uploads.py` using `APIRouter`.
- **Why:** App setup registers routes while upload handling stays in its own focused file.
- **Trade-off or limitation:** A route module must be registered with the app or its routes are unavailable.
- **Files affected:** `app/main.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Receive uploads as `UploadFile` with `File(...)`

- **Decision:** Declare the required upload parameter as `file: UploadFile = File(...)`.
- **Why:** FastAPI then receives it from a multipart request and provides file-like read, seek, and close operations.
- **Trade-off or limitation:** The request's filename and MIME type are supplied by the client and do not prove the file's actual format.
- **Files affected:** `app/api/uploads.py`, `app/services/validation.py`, `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Check the PDF signature and rewind before saving

- **Decision:** Search the first 1,024 bytes for `%PDF-`, then call `seek(0)`.
- **Why:** The signature is a basic contents check; rewinding lets storage read the full file from its first byte.
- **Trade-off or limitation:** This is not full PDF parsing and does not prove a file is safe or usable. MIME type is informational only.
- **Files affected:** `app/services/validation.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Limit uploads and save in chunks

- **Decision:** Read and save 1 MiB chunks, rejecting uploads after their cumulative size exceeds 25 MiB by default.
- **Why:** Chunking avoids loading the entire upload into application memory; counting bytes while saving enforces the limit even if request metadata is inaccurate.
- **Trade-off or limitation:** The limit may need adjustment for real workloads. The maximum can be configured; the chunk size is fixed in code.
- **Files affected:** `app/settings.py`, `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Store uploads under generated UUID names

- **Decision:** Use a generated UUID for the stored PDF filename rather than the client filename.
- **Why:** The client filename does not control a filesystem path and same-name uploads do not collide.
- **Trade-off or limitation:** The UUID is an identifier, not access control. Upload metadata is not yet persisted separately from jobs.
- **Files affected:** `app/storage/local.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Write to a temporary file and rename after success

- **Decision:** Create a temporary `.uploading` file with exclusive-create mode and rename it to `.pdf` only after the write completes.
- **Why:** An incomplete write does not appear under the final filename; exclusive creation avoids overwriting an existing temporary file.
- **Trade-off or limitation:** This does not guarantee durability through power loss or filesystem failure. The code attempts to remove the temporary file after an exception.
- **Files affected:** `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Reject empty uploads and always close the request file

- **Decision:** Reject empty files and close `UploadFile` in a `finally` block.
- **Why:** Empty input is not useful for PDF processing; `finally` releases upload resources on both success and failure.
- **Trade-off or limitation:** The route's signature check rejects an empty file before storage; storage also has a defensive empty check that is normally not reached through the route.
- **Files affected:** `app/services/validation.py`, `app/storage/local.py`, `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-15 — Centralize local upload settings

- **Decision:** Keep the upload directory, upload limit, and chunk size in `app/settings.py`.
- **Why:** Storage behavior uses named configuration values instead of scattering them through the route.
- **Trade-off or limitation:** The upload directory and size limit can be set with environment variables; chunk size is fixed at 1 MiB.
- **Files affected:** `app/settings.py`, `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-17 — Persist jobs in SQLite

- **Decision:** Store jobs in a local SQLite database at `data/jobs.sqlite3` by default, using Python's built-in `sqlite3` module.
- **Why:** A job record should survive an API restart. SQLite needs no separate server or paid service, and direct SQL keeps the data operations visible for this learning project.
- **Trade-off or limitation:** This is a local, single-machine store. SQLite writes are serialized; it is not a distributed queue. The database path can be changed with `PDFFORGE_DATABASE_PATH`.
- **Files affected:** `app/db.py`, `app/settings.py`, `app/repositories/jobs.py`, `app/main.py`, `app/worker.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-17 — Represent work with a separate job ID and status

- **Decision:** Each saved upload gets a separate UUID job record with `queued`, `processing`, `completed`, or `failed` status. The upload response returns both IDs.
- **Why:** The upload ID identifies the saved file; the job ID identifies work and lets the client ask for its status.
- **Trade-off or limitation:** The job is created after the file is saved. If database insertion fails, the uploaded file can remain without a job. The current worker only checks that the file exists; it does not process PDF contents.
- **Files affected:** `app/api/uploads.py`, `app/repositories/jobs.py`, `app/api/jobs.py`, `app/db.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-17 — Use a separate worker that polls SQLite

- **Decision:** Run `app/worker.py` as a separate process. It polls for queued jobs, claims one, checks the upload exists, and records a final state. The poll interval is one second.
- **Why:** The API can save a job and return without waiting for processing. Keeping the worker separate makes the job lifecycle visible and testable as a backend concept.
- **Trade-off or limitation:** Polling adds up to about one second of idle pickup delay and performs repeated database checks. A worker crash after claiming a job can leave it in `processing`; automatic recovery and retries are not implemented. No Redis or Celery is used.
- **Files affected:** `app/worker.py`, `app/repositories/jobs.py`, `app/settings.py`, `app/storage/local.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-17 — Expose job status through an API route

- **Decision:** Add `GET /jobs/{job_id}` to return a job record, or HTTP 404 if it does not exist.
- **Why:** The browser needs a way to check progress after receiving a job ID.
- **Trade-off or limitation:** There is no authentication or ownership check in this learning version; anyone who knows a job ID can query it.
- **Files affected:** `app/api/jobs.py`, `app/main.py`, `app/repositories/jobs.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-17 — Return IDs and status as JSON with HTTP 201

- **Decision:** Successful upload responses use HTTP 201 Created and return JSON metadata including both `upload_id` and `job_id`, plus the initial job status.
- **Why:** The client needs the identifiers to distinguish the saved file from its job and to request progress later.
- **Trade-off or limitation:** The response does not mean the worker has processed the PDF; it means the upload was saved and the job was queued.
- **Files affected:** `app/api/uploads.py`.
- **Status:** Implemented; not verified by tests.

## 2026-10-17 — Initialize the database at API and worker startup

- **Decision:** Create the jobs table if missing when the API starts and when the worker starts.
- **Why:** Either process can be started first, and both need the schema to exist before using jobs.
- **Trade-off or limitation:** Schema creation is idempotent, but there is no migration system yet for changing an existing schema.
- **Files affected:** `app/db.py`, `app/main.py`, `app/worker.py`.
- **Status:** Implemented; not verified by tests.

## Future maintenance

Update this file whenever a meaningful technical decision is proposed, approved, implemented, or rejected. Keep status accurate; do not mark a choice verified without actual verification.
