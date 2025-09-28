"""API entrypoint for the Tree Signal service."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from tree_signal.core import ChannelTreeService, Message, MessageSeverity

from .schemas import MessageIngress, MessageIngressResponse

app = FastAPI(title="Tree Signal", version="0.1.0")
app.state.tree_service = ChannelTreeService()


def get_tree_service() -> ChannelTreeService:
    """Retrieve the shared channel tree service instance."""

    return app.state.tree_service  # type: ignore[return-value]


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


@app.post("/v1/messages", response_model=MessageIngressResponse, status_code=202)
async def ingest_message(payload: MessageIngress) -> MessageIngressResponse:
    """Accept a message for inclusion in the channel tree."""

    segments = tuple(segment for segment in payload.channel.split(".") if segment)
    if not segments:
        raise HTTPException(status_code=422, detail="channel path must not be empty")

    try:
        severity = MessageSeverity(payload.severity.lower())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid severity value") from exc

    tree_service = get_tree_service()
    message_id = uuid4().hex
    message = Message(
        id=message_id,
        channel_path=segments,
        payload=payload.payload,
        received_at=datetime.now(tz=timezone.utc),
        severity=severity,
        metadata=payload.metadata,
    )

    tree_service.ingest(message)

    return MessageIngressResponse(id=message_id)
