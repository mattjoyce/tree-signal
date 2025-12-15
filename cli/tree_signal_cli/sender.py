"""
API message sender with batching, rate limiting, and retry logic.

Handles sending messages to the Tree Signal API with configurable
performance tuning and error handling.
"""

import sys
import time
import urllib.request
import urllib.error
import json
from collections import deque
from typing import Any


class MessageSender:
    """
    Sends messages to Tree Signal API with batching and rate limiting.

    Uses token bucket algorithm for rate limiting and exponential backoff for retries.
    """

    def __init__(
        self,
        api_url: str,
        api_key: str | None = None,
        batch_size: int = 1,
        batch_interval: float = 1.0,
        rate_limit: int = 0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 30.0,
        timeout: float = 5.0,
        dry_run: bool = False,
        debug: bool = False,
    ):
        """
        Initialize message sender.

        Args:
            api_url: Base URL of Tree Signal API
            api_key: Optional API key for authentication
            batch_size: Messages to accumulate before sending
            batch_interval: Max seconds to wait before flushing batch
            rate_limit: Max messages per second (0 = unlimited)
            max_retries: Number of retry attempts on failure
            retry_base_delay: Base delay for exponential backoff (seconds)
            retry_max_delay: Max delay cap for backoff (seconds)
            timeout: HTTP request timeout (seconds)
            dry_run: If True, print messages instead of sending
            debug: Enable debug logging
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        self.timeout = timeout
        self.dry_run = dry_run
        self.debug = debug

        self.batch: list[dict] = []
        self.batch_start_time = time.time()

        # Rate limiting (token bucket)
        self.tokens = float(rate_limit) if rate_limit > 0 else float('inf')
        self.last_token_update = time.time()

    def send(self, channel: str, payload: str, severity: str = "info") -> None:
        """
        Queue a message for sending (batches automatically).

        Args:
            channel: Hierarchical channel path (e.g., "app.api.auth")
            payload: Message content
            severity: Message severity level
        """
        # Normalize severity to API values: debug|info|warn|error
        severity_map = {
            "warning": "warn",
            "critical": "error",
            "fatal": "error",
        }
        severity = severity_map.get(severity.lower(), severity.lower())

        message = {
            "channel": channel,
            "payload": payload,
            "severity": severity,
        }

        self.batch.append(message)

        # Flush if batch is full or interval exceeded
        if len(self.batch) >= self.batch_size or \
           (time.time() - self.batch_start_time) >= self.batch_interval:
            self.flush()

    def flush(self) -> None:
        """Flush any pending messages in the batch."""
        if not self.batch:
            return

        # Rate limiting check
        self._refill_tokens()
        if self.rate_limit > 0 and self.tokens < len(self.batch):
            if self.debug:
                print(f"[DEBUG] Rate limit: waiting for tokens", file=sys.stderr)
            time.sleep(0.1)
            return  # Will retry on next flush

        # Send batch
        for msg in self.batch:
            if self.dry_run:
                print(f"[DRY-RUN] {msg['channel']} [{msg['severity']}] {msg['payload']}")
            else:
                self._send_single(msg)
                self.tokens -= 1

        self.batch = []
        self.batch_start_time = time.time()

    def _refill_tokens(self) -> None:
        """Refill rate limit tokens based on elapsed time."""
        if self.rate_limit == 0:
            return

        now = time.time()
        elapsed = now - self.last_token_update
        self.tokens = min(self.rate_limit, self.tokens + (elapsed * self.rate_limit))
        self.last_token_update = now

    def _send_single(self, message: dict) -> None:
        """
        Send a single message to the API with retry logic.

        Args:
            message: Message dict with channel, payload, severity

        Raises:
            SystemExit: On authentication error or max retries exceeded
        """
        url = f"{self.api_url}/v1/messages"
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        data = json.dumps(message).encode("utf-8")

        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    if self.debug:
                        print(f"[DEBUG] Sent: {message['channel']} [{message['severity']}]", file=sys.stderr)
                    return  # Success

            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    print(f"ERROR: Authentication failed (HTTP {e.code})", file=sys.stderr)
                    sys.exit(3)

                if attempt < self.max_retries:
                    delay = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                    if self.debug:
                        print(f"[DEBUG] HTTP {e.code}, retry {attempt+1}/{self.max_retries} in {delay}s", file=sys.stderr)
                    time.sleep(delay)
                else:
                    print(f"ERROR: Failed after {self.max_retries} retries: HTTP {e.code}", file=sys.stderr)
                    sys.exit(2)

            except urllib.error.URLError as e:
                if attempt < self.max_retries:
                    delay = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                    if self.debug:
                        print(f"[DEBUG] Connection error, retry {attempt+1}/{self.max_retries} in {delay}s", file=sys.stderr)
                    time.sleep(delay)
                else:
                    print(f"ERROR: Cannot connect to API: {e.reason}", file=sys.stderr)
                    sys.exit(2)

            except Exception as e:
                print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
                sys.exit(1)

    def close(self) -> None:
        """Flush any remaining messages before shutdown."""
        self.flush()
