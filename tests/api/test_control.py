from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tree_signal.api.main import app, get_tree_service
from tree_signal.core import ChannelTreeService
from tree_signal.core.models import Message, MessageSeverity


@pytest.fixture(autouse=True)
def reset_tree_service() -> None:
    app.state.tree_service = ChannelTreeService()


def _message(channel: str) -> Message:
    return Message(
        id="msg",
        channel_path=tuple(channel.split(".")),
        payload="payload",
        received_at=datetime.now(tz=timezone.utc),
        severity=MessageSeverity.INFO,
        metadata=None,
    )


@pytest.mark.asyncio
async def test_update_decay_applies_configuration() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/control/decay",
            json={"hold_seconds": 20, "decay_seconds": 15},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"hold_seconds": 20.0, "decay_seconds": 15.0}


@pytest.mark.asyncio
async def test_prune_channel_removes_subtree() -> None:
    service = get_tree_service()
    service.ingest(_message("alpha.beta"))
    service.ingest(_message("alpha.gamma"))

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/control/prune",
            json={"channel": "alpha.beta"},
        )

    assert response.status_code == 204
    node = service.get_node(("alpha", "beta"))
    assert node is None


@pytest.mark.asyncio
async def test_control_endpoints_validate_channel() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/control/prune",
            json={"channel": "."},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "channel path must not be empty"


@pytest.mark.asyncio
async def test_decay_validation_requires_positive_values() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/control/decay",
            json={"hold_seconds": 1, "decay_seconds": 0},
        )

    assert response.status_code == 422
