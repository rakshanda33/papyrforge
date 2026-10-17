# PDFForge execution flow

This file documents the current code path. The worker currently checks that an uploaded file exists; it does not yet inspect or transform PDF contents.

## Application startup

1. The ASGI server imports `app.main` and uses its `app` object.
2. `app.main` imports the upload and job routers and `initialize_database()`.
3. FastAPI starts the `lifespan()` function. It calls `initialize_database()`, which creates the parent folder for `DATABASE_PATH` and creates the `jobs` table and status index if they are missing.
4. The app registers the routers. The available routes are `POST /uploads`, `GET /jobs/{job_id}`, and `GET /health`.

The worker is a separate process started from the project folder with `python -m app.worker`. It also calls `initialize_database()` before polling, so the worker can be started before or after the API.

## Upload and job creation

```text
Browser --multipart POST /uploads--> upload_pdf()
                                      │
                                      ├─ check PDF signature and rewind stream
                                      ├─ save chunks under upload UUID
                                      ├─ close incoming UploadFile
                                      ├─ create SQLite job with status queued
                                      └─ return upload_id + job_id + queued status
```

1. FastAPI parses the multipart request and passes an `UploadFile` to `upload_pdf()` in `app/api/uploads.py`.
2. `upload_pdf()` calls `read_and_validate_pdf_header(file)` in `app/services/validation.py`.
3. Validation reads up to 1,024 bytes, calls `seek(0)`, and checks for `%PDF-`. Empty input raises HTTP 400; no signature raises HTTP 415. This check does not parse or prove the full PDF is safe.
4. If validation succeeds, `upload_pdf()` calls `save_pdf(file)` in `app/storage/local.py`.
5. `save_pdf()` creates `UPLOAD_DIR`, generates an upload UUID, and opens a hidden temporary file with exclusive-create mode. It reads up to `UPLOAD_CHUNK_BYTES` per iteration, counts bytes, rejects the upload with HTTP 413 if the running count exceeds `MAX_UPLOAD_BYTES`, and writes allowed chunks.
6. An empty input raises HTTP 400. On success, the temporary file is renamed to `<upload_id>.pdf`; `save_pdf()` returns `(upload_id, size_bytes)`.
7. The `finally` block in `upload_pdf()` closes the incoming `UploadFile` on success or failure of validation/storage.
8. After the file is saved and the request upload is closed, `upload_pdf()` calls `create_job(upload_id)` in `app/repositories/jobs.py`.
9. `create_job()` makes a separate UUID for the job, sets the initial status to `queued`, records UTC creation/update timestamps, and inserts the record through `database_connection()` from `app/db.py`.
10. The upload route returns JSON with `upload_id`, `job_id`, `status`, original filename, size in bytes, and a message. Successful upload responses use HTTP 201 Created.

The upload ID names the saved file. The job ID names the processing record. Creating a job happens after saving the file; if the database insert fails, the file may remain without a job record.

## Worker flow

```text
`run_worker()`
  ├─ initialize SQLite schema
  └─ repeat:
       ├─ `claim_next_job()` → oldest queued job becomes processing
       ├─ if no job: sleep 1 second
       └─ check `upload_exists(upload_id)`
            ├─ file exists → mark completed
            └─ missing/inaccessible → mark failed with a safe message
```

1. `run_worker()` in `app/worker.py` initializes the database, then loops.
2. It calls `claim_next_job()` in `app/repositories/jobs.py`.
3. `claim_next_job()` starts a SQLite `BEGIN IMMEDIATE` transaction, selects the oldest `queued` job, and changes it to `processing`. The write reservation prevents two workers from claiming the same queued row at once.
4. If there is no queued job, the worker sleeps for `WORKER_POLL_INTERVAL_SECONDS` (one second) and checks again.
5. For a claimed job, the worker calls `upload_exists(upload_id)` in `app/storage/local.py`. That function parses the saved UUID and checks for its `.pdf` file under `UPLOAD_DIR`.
6. If the file exists, `finish_job()` changes the status from `processing` to `completed`. If it is missing, the worker sets `failed` and stores `Saved upload was not found.` An `OSError` while checking becomes `failed` with `Could not access the saved upload.`
7. This milestone does no PDF parsing, conversion, or compression. `completed` means only that the worker found the saved file.

## Checking job status

1. The browser requests `GET /jobs/{job_id}`.
2. `read_job()` in `app/api/jobs.py` calls `get_job(job_id)` in `app/repositories/jobs.py`.
3. `get_job()` runs a parameterized SQLite query and returns the saved row as a dictionary.
4. If the ID is unknown, the route raises HTTP 404 with `Job not found.` Otherwise, FastAPI returns the job fields as JSON: IDs, status, timestamps, and optional error message.

## Database behavior and configuration

- `app/settings.py` sets `DATABASE_PATH` to `data/jobs.sqlite3` by default; `PDFFORGE_DATABASE_PATH` can override it.
- `app/db.py` creates the database parent directory and opens/closes SQLite connections. Its context manager commits successful work and rolls back when an exception occurs.
- `initialize_database()` creates the `jobs` table if needed. A database constraint allows only `queued`, `processing`, `completed`, and `failed` statuses.
- The upload directory defaults to `data/uploads`; the database and uploads are both local files. Database writes are synchronous and small in this milestone.

## Other route and failure behavior

- `GET /health` calls `health()` in `app/main.py`, which returns `{"status": "ok"}` as JSON. It does not check the database or worker.
- Validation/storage errors happen before job creation. The upload file is closed in `finally`; `save_pdf()` attempts to delete its temporary file if saving raises.
- If job insertion fails after upload storage succeeded, the request fails but the saved PDF may remain without a corresponding job.
- If an unexpected worker failure happens after a job is claimed, the record may remain `processing`. Automatic retries or stale-job recovery are not implemented.

## Future maintenance

Update this file whenever an approved code change alters startup, request flow, function calls, data flow, cleanup, or error handling.
