from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tree_signal.api.main import app, get_tree_service
from tree_signal.core import ChannelTreeService, Message, MessageSeverity


@pytest.fixture(autouse=True)
def reset_tree_service() -> None:
    app.state.tree_service = ChannelTreeService()


def _message(path: tuple[str, ...], *, at: datetime) -> Message:
    return Message(
        id="msg",
        channel_path=path,
        payload="payload",
        received_at=at,
        severity=MessageSeverity.INFO,
        metadata=None,
    )


@pytest.mark.asyncio
async def test_layout_endpoint_returns_frames() -> None:
    service = get_tree_service()
    now = datetime.now(tz=timezone.utc)
    service.ingest(_message(("alpha",), at=now))
    service.ingest(_message(("beta",), at=now))

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/layout")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["rect"]["width"] == 1.0


@pytest.mark.asyncio
async def test_layout_endpoint_handles_empty_tree() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/layout")

    assert response.status_code == 200
    assert response.json() == []
