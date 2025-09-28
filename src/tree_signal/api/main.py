"""API entrypoint for the Tree Signal service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response

from tree_signal.core import ChannelTreeService, Message, MessageSeverity
from tree_signal.layout import LinearLayoutGenerator

from .schemas import (
    DecayConfig,
    DecayConfigResponse,
    LayoutFrameResponse,
    MessageIngress,
    MessageIngressResponse,
    MessageRecord,
    PruneRequest,
)

app = FastAPI(title="Tree Signal", version="0.1.0")
app.state.tree_service = ChannelTreeService()
app.state.layout_generator = LinearLayoutGenerator()


def get_tree_service() -> ChannelTreeService:
    """Retrieve the shared channel tree service instance."""

    return app.state.tree_service  # type: ignore[return-value]


def get_layout_generator() -> LinearLayoutGenerator:
    """Retrieve the shared layout generator instance."""

    return app.state.layout_generator  # type: ignore[return-value]


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

    segments = _parse_channel(payload.channel)

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


@app.get("/v1/messages/{channel}", response_model=List[MessageRecord])
async def list_messages(channel: str) -> List[MessageRecord]:
    """Return the recent message history for a channel."""

    segments = _parse_channel(channel)
    tree_service = get_tree_service()
    history = tree_service.get_history(segments)
    return [MessageRecord.from_domain(msg) for msg in history]


@app.post("/v1/control/decay", response_model=DecayConfigResponse)
async def update_decay(config: DecayConfig) -> DecayConfigResponse:
    """Update decay configuration for the channel tree."""

    tree_service = get_tree_service()
    hold, decay = config.to_timedelta()
    tree_service.configure_decay(hold=hold, decay=decay)
    return DecayConfigResponse(hold_seconds=config.hold_seconds, decay_seconds=config.decay_seconds)


@app.post("/v1/control/prune", status_code=204, response_class=Response)
async def prune_channel(request: PruneRequest) -> Response:
    """Remove a channel subtree."""

    segments = _parse_channel(request.channel)
    tree_service = get_tree_service()
    tree_service.prune(segments)
    return Response(status_code=204)


@app.get("/v1/layout", response_model=List[LayoutFrameResponse])
async def get_layout() -> List[LayoutFrameResponse]:
    """Return the current layout frames for active panels."""

    tree_service = get_tree_service()
    generator = get_layout_generator()
    frames = generator.generate(tree_service, timestamp=datetime.now(tz=timezone.utc))
    return [LayoutFrameResponse.from_domain(frame) for frame in frames]


def _parse_channel(raw: str) -> tuple[str, ...]:
    segments = tuple(segment for segment in raw.split(".") if segment)
    if not segments:
        raise HTTPException(status_code=422, detail="channel path must not be empty")
    return segments
