from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tree_signal.api.main import app, get_tree_service
from tree_signal.core import ChannelTreeService


@pytest.fixture(autouse=True)
def reset_tree_service() -> None:
    app.state.tree_service = ChannelTreeService()


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
