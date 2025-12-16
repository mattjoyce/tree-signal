"""API entrypoint for the Tree Signal service."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from tree_signal.core import ChannelTreeService, ColorService, Message, MessageSeverity, get_config
from tree_signal.layout import LinearLayoutGenerator

from .schemas import (
    ClientConfigResponse,
    ColorConfig,
    ColorConfigResponse,
    DecayConfig,
    DecayConfigResponse,
    LayoutFrameResponse,
    MessageIngress,
    MessageIngressResponse,
    MessageRecord,
    PruneRequest,
)

# Load configuration at startup
config = get_config()

app = FastAPI(title="Tree Signal", version=config.client.version)
app.state.tree_service = ChannelTreeService()
app.state.color_service = ColorService(
    mode=config.client.colors.assignment_mode,
    inheritance_mode=config.client.colors.inheritance_mode
)
app.state.layout_generator = LinearLayoutGenerator(color_service=app.state.color_service)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] ,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/v1/control/colors", response_model=ColorConfigResponse)
async def update_colors(config: ColorConfig) -> ColorConfigResponse:
    """Update color assignment and inheritance configuration."""

    # Create new ColorService with updated configuration
    new_color_service = ColorService(mode=config.assignment_mode, inheritance_mode=config.inheritance_mode)

    # Update app state
    app.state.color_service = new_color_service
    app.state.layout_generator = LinearLayoutGenerator(color_service=new_color_service)

    return ColorConfigResponse(
        assignment_mode=config.assignment_mode, inheritance_mode=config.inheritance_mode
    )


@app.get("/v1/control/colors", response_model=ColorConfigResponse)
async def get_colors() -> ColorConfigResponse:
    """Get current color configuration."""

    color_service = app.state.color_service
    return ColorConfigResponse(
        assignment_mode=color_service.mode, inheritance_mode=color_service.inheritance_mode
    )


@app.get("/v1/client/config", response_model=ClientConfigResponse)
async def get_client_config() -> ClientConfigResponse:
    """Return client configuration for dashboard."""

    config = get_config()
    return ClientConfigResponse.from_domain(config.client)


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


# Mount static files (client dashboard) - must be last to not override API routes
CLIENT_DIR = Path(__file__).parent.parent.parent.parent / "client"
if CLIENT_DIR.exists():
    app.mount("/", StaticFiles(directory=str(CLIENT_DIR), html=True), name="static")
