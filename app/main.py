"""PDFForge API entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.jobs import router as jobs_router
from app.api.uploads import router as uploads_router
from app.db import initialize_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create the job table before the API starts serving requests."""
    initialize_database()
    yield


app = FastAPI(title="PDFForge", version="0.1.0", lifespan=lifespan)
app.include_router(uploads_router)
app.include_router(jobs_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
