from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tree_signal.api.main import app, get_tree_service
from tree_signal.core import ChannelTreeService
from tree_signal.core.models import Message, MessageSeverity


@pytest.fixture(autouse=True)
def reset_tree_service() -> None:
    app.state.tree_service = ChannelTreeService()


def _message(channel: str, *, at: datetime) -> Message:
    return Message(
        id="msg",
        channel_path=tuple(channel.split(".")),
        payload="payload",
        received_at=at,
        severity=MessageSeverity.INFO,
        metadata=None,
    )


@pytest.mark.asyncio
async def test_ingest_message_accepts_valid_payload() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/messages",
            json={
                "channel": "alpha.beta",
                "payload": "hello",
                "severity": "info",
            },
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert len(body["id"]) == 32

    service = get_tree_service()
    node = service.get_node(("alpha", "beta"))
    assert node is not None
    assert node.weight == 1.0


@pytest.mark.asyncio
async def test_ingest_message_rejects_empty_channel() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/messages",
            json={
                "channel": ".",
                "payload": "bad",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "channel path must not be empty"


@pytest.mark.asyncio
async def test_ingest_message_rejects_invalid_severity() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/messages",
            json={
                "channel": "alpha",
                "payload": "hi",
                "severity": "critical",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid severity value"


@pytest.mark.asyncio
async def test_list_messages_returns_history() -> None:
    now = datetime.now(tz=timezone.utc)
    service = get_tree_service()
    service.ingest(_message("alpha.beta", at=now))

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/messages/alpha.beta")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["channel"] == ["alpha", "beta"]
    assert payload[0]["payload"] == "payload"


@pytest.mark.asyncio
async def test_list_messages_requires_channel() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/messages/%2E")

    assert response.status_code == 422
    assert response.json()["detail"] == "channel path must not be empty"
