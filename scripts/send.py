"""Send a single message to the Tree Signal API via CLI arguments."""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a message to the Tree Signal API")
    parser.add_argument("message", help="Message payload to send")
    parser.add_argument("channel", help="Channel path, e.g. alpha.beta")
    parser.add_argument("--port", type=int, default=8000, help="API port (defaults to 8000)")
    parser.add_argument("--host", default="localhost", help="API host (defaults to localhost)")
    parser.add_argument("--severity", default="info", choices=["debug", "info", "warn", "error"], help="Message severity")
    return parser.parse_args()


def send_message(host: str, port: int, channel: str, payload: str, severity: str) -> None:
    base_url = os.getenv("TREE_SIGNAL_API", f"http://{host}:{port}")
    api_key = os.getenv("TREE_SIGNAL_API_KEY")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    message_id = uuid4().hex
    data = {
        "channel": channel,
        "payload": f"[{message_id[:6]}] {payload}",
        "severity": severity,
        "metadata": {"sent_at": datetime.now(tz=timezone.utc).isoformat()},
    }

    response = httpx.post(f"{base_url}/v1/messages", json=data, headers=headers, timeout=5.0)
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    args = parse_args()
    send_message(args.host, args.port, args.channel, args.message, args.severity)
