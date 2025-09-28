"""Send a single message to the Tree Signal API."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx

API_BASE = os.getenv("TREE_SIGNAL_API", "http://localhost:8000")
API_KEY = os.getenv("TREE_SIGNAL_API_KEY")


def send_message(channel: str, payload: str, severity: str = "info") -> None:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY

    message_id = uuid4().hex
    data = {
        "channel": channel,
        "payload": f"[{message_id[:6]}] {payload}",
        "severity": severity,
        "metadata": {"sent_at": datetime.now(tz=timezone.utc).isoformat()},
    }
    with httpx.Client(base_url=API_BASE, timeout=5.0) as client:
        response = client.post("/v1/messages", json=data, headers=headers)
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    send_message("demo.panel", "Hello from Python")
