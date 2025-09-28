import pytest
from httpx import AsyncClient

from tree_signal.api.main import app


@pytest.mark.asyncio
async def test_healthcheck() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "tree-signal"
    assert payload["status"] == "ok"
