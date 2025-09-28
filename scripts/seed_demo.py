"""Seed the Tree Signal API with demo messages for the client dashboard."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx

API_BASE = os.getenv("TREE_SIGNAL_API", "http://localhost:8000")
API_KEY = os.getenv("TREE_SIGNAL_API_KEY")

CHANNELS = [
    "alpha.beta",
    "alpha.gamma",
    "bravo.main",
    "charlie.ops.alerts",
    "delta",
]

PAYLOADS = [
    "Startup complete",
    "Processing batch #241",
    "Latency spike detected",
    "Recovered from degraded state",
    "Scheduled maintenance window",
]

async def send_message(client: httpx.AsyncClient, channel: str, payload: str, severity: str = "info") -> None:
    message_id = uuid4().hex
    data = {
        "channel": channel,
        "payload": f"[{message_id[:6]}] {payload}",
        "severity": severity,
        "metadata": {"seeded_at": datetime.now(tz=timezone.utc).isoformat()},
    }
    response = await client.post("/v1/messages", json=data)
    response.raise_for_status()


async def main() -> None:
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY

    async with httpx.AsyncClient(base_url=API_BASE, headers=headers, timeout=5.0) as client:
        tasks = []
        for index, channel in enumerate(CHANNELS):
            severity = "warn" if "alerts" in channel else "info"
            payload = PAYLOADS[index % len(PAYLOADS)]
            tasks.append(send_message(client, channel, payload, severity=severity))
        await asyncio.gather(*tasks)

    print(f"Seeded demo messages via {API_BASE}. Reload the client dashboard to view updates.")


if __name__ == "__main__":
    asyncio.run(main())
