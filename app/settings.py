"""Small, environment-configurable settings for PDFForge."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("PDFFORGE_UPLOAD_DIR", PROJECT_ROOT / "data" / "uploads"))
MAX_UPLOAD_BYTES = int(os.getenv("PDFFORGE_MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
UPLOAD_CHUNK_BYTES = 1024 * 1024
DATABASE_PATH = Path(os.getenv("PDFFORGE_DATABASE_PATH", PROJECT_ROOT / "data" / "jobs.sqlite3"))
WORKER_POLL_INTERVAL_SECONDS = 1
