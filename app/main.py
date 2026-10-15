"""PDFForge API entry point."""

from fastapi import FastAPI

from app.api.uploads import router as uploads_router


app = FastAPI(title="PDFForge", version="0.1.0")
app.include_router(uploads_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
