"""
Message routing engine with pattern matching and channel templating.

Supports:
- Regex pattern matching with named capture groups
- Channel templating using captured variables
- JSON extraction from structured logs
- Severity mapping based on patterns
"""

import json
import re
from typing import Any


class RoutingResult:
    """Result of routing a log line to a channel."""

    def __init__(self, channel: str, payload: str, severity: str = "info"):
        self.channel = channel
        self.payload = payload
        self.severity = severity

    def __repr__(self):
        return f"RoutingResult(channel='{self.channel}', severity='{self.severity}')"


class Router:
    """
    Routes log lines to Tree Signal channels based on configured rules.

    Rules are evaluated in order; first match wins.
    """

    def __init__(self, routing_rules: list[dict[str, Any]], default_channel: str | None = None, default_severity: str = "info"):
        """
        Initialize router with routing rules.

        Args:
            routing_rules: List of routing rule dicts from config
            default_channel: Fallback channel if no rules match
            default_severity: Default severity level
        """
        self.rules = routing_rules
        self.default_channel = default_channel
        self.default_severity = default_severity
        self.compiled_patterns: dict[int, re.Pattern] = {}

        # Pre-compile regex patterns
        for idx, rule in enumerate(self.rules):
            if "pattern" in rule:
                self.compiled_patterns[idx] = re.compile(rule["pattern"])

    def route(self, line: str, cli_channel: str | None = None) -> RoutingResult:
        """
        Route a log line to a channel based on configured rules.

        Args:
            line: The log line to route
            cli_channel: Channel from CLI arg (used as fallback or template variable)

        Returns:
            RoutingResult with channel, payload, and severity

        Raises:
            ValueError: If no channel can be determined
        """
        line = line.rstrip('\n\r')

        # Try each routing rule in order
        for idx, rule in enumerate(self.rules):
            pattern = self.compiled_patterns.get(idx)
            if not pattern:
                continue

            match = pattern.search(line)
            if not match:
                continue

            # Extract variables from named groups
            variables = match.groupdict()

            # Handle JSON extraction if specified
            if "json_extract" in rule:
                result = self._extract_from_json(line, rule["json_extract"], variables)
                if result:
                    return result

            # Build channel from template
            channel_template = rule.get("channel", "{channel}")
            variables["channel"] = cli_channel or self.default_channel or "unknown"
            channel = self._template_channel(channel_template, variables)

            # Determine severity
            severity = rule.get("severity", self.default_severity)
            if "severity_map" in rule:
                severity = self._map_severity(variables, rule["severity_map"], severity)
            # If severity is a template variable, resolve it
            severity = variables.get(severity, severity)

            payload = variables.get("message", line)

            return RoutingResult(channel=channel, payload=payload, severity=severity)

        # No rules matched - use CLI channel or default
        if cli_channel:
            return RoutingResult(
                channel=cli_channel,
                payload=line,
                severity=self.default_severity
            )

        if self.default_channel:
            return RoutingResult(
                channel=self.default_channel,
                payload=line,
                severity=self.default_severity
            )

        raise ValueError(f"No routing rule matched and no default channel configured")

    def _extract_from_json(self, line: str, json_config: dict, variables: dict) -> RoutingResult | None:
        """
        Extract channel/severity/message from JSON log line.

        Args:
            line: The log line (should be JSON)
            json_config: Config with keys: channel, severity, message
            variables: Existing variables from regex match

        Returns:
            RoutingResult if extraction succeeds, None otherwise
        """
        try:
            data = json.loads(line)

            # Extract nested values using dot notation (e.g., "log.service")
            channel = self._get_nested(data, json_config.get("channel", "channel"))
            severity = self._get_nested(data, json_config.get("severity", "severity"))
            payload = self._get_nested(data, json_config.get("message", "message"))

            # Fallback to original line if extraction fails
            channel = channel or variables.get("channel", "unknown")
            severity = severity or self.default_severity
            payload = payload or line

            return RoutingResult(
                channel=str(channel),
                payload=str(payload),
                severity=str(severity)
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _get_nested(self, data: dict, path: str) -> Any:
        """
        Get nested value from dict using dot notation.

        Example: "log.service" returns data["log"]["service"]
        """
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _template_channel(self, template: str, variables: dict) -> str:
        """
        Replace {variables} in channel template.

        Example: "app.{service}.{level}" with {service: "api", level: "error"}
                 returns "app.api.error"

        Sanitizes channel parts: lowercase, replace invalid chars with underscore.
        """
        # Replace variables
        channel = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if placeholder in channel:
                # Sanitize: lowercase, replace non-alphanumeric with underscore
                sanitized = re.sub(r'[^a-zA-Z0-9.]', '_', str(value)).lower()
                channel = channel.replace(placeholder, sanitized)

        return channel

    def _map_severity(self, variables: dict, severity_map: dict, default: str) -> str:
        """
        Map a captured variable to severity using regex patterns.

        Example: severity_map = {"^5\\d\\d$": "error", "^2\\d\\d$": "info"}
                 If variables["status"] = "500", returns "error"
        """
        for pattern_str, severity in severity_map.items():
            pattern = re.compile(pattern_str)
            for var_value in variables.values():
                if pattern.match(str(var_value)):
                    return severity
        return default
