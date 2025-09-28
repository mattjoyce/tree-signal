"""API entrypoint for the Tree Signal service."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Tree Signal", version="0.1.0")


@app.get("/healthz", summary="Health check")
async def healthcheck() -> JSONResponse:
    """Return a simple heartbeat used by deployment tooling."""
    return JSONResponse(content={"status": "ok"})


@app.get("/", summary="Service metadata")
async def root() -> JSONResponse:
    """Lightweight landing endpoint for manual verification."""
    return JSONResponse(
        content={
            "service": "tree-signal",
            "status": "ok",
            "message": "Treemap prototype is warming up.",
        }
    )
