"""Basic tests for message routing."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tree_signal_cli.router import Router, RoutingResult


def test_simple_routing():
    """Test basic routing with default channel."""
    router = Router(routing_rules=[], default_channel="default.logs")

    result = router.route("Test log message")

    assert result.channel == "default.logs"
    assert result.payload == "Test log message"
    assert result.severity == "info"


def test_pattern_matching():
    """Test regex pattern matching."""
    rules = [
        {
            "name": "errors",
            "pattern": r".*ERROR.*",
            "channel": "app.errors",
            "severity": "error",
        }
    ]

    router = Router(routing_rules=rules, default_channel="default")

    # Should match error pattern
    result = router.route("2024-01-15 ERROR: Database connection failed")
    assert result.channel == "app.errors"
    assert result.severity == "error"

    # Should fall back to default
    result = router.route("2024-01-15 INFO: All good")
    assert result.channel == "default"
    assert result.severity == "info"


def test_named_groups_templating():
    """Test named capture groups and channel templating."""
    rules = [
        {
            "name": "nginx",
            "pattern": r'^(?P<ip>[\d.]+).*?"(?P<method>\w+) (?P<path>/\S+).*?" (?P<status>\d+)',
            "channel": "nginx.{method}",
        }
    ]

    router = Router(routing_rules=rules)

    log = '192.168.1.1 - - [15/Jan/2024:10:00:00] "GET /api/users HTTP/1.1" 200'
    result = router.route(log)

    assert result.channel == "nginx.get"  # Should be lowercase/sanitized
    assert result.severity == "info"


def test_json_extraction():
    """Test JSON log extraction."""
    rules = [
        {
            "name": "json",
            "pattern": r'^(?P<json>\{.*\})$',
            "json_extract": {
                "channel": "service",
                "severity": "level",
                "message": "msg",
            }
        }
    ]

    router = Router(routing_rules=rules)

    log = '{"service": "api", "level": "error", "msg": "DB timeout"}'
    result = router.route(log)

    assert result.channel == "api"
    assert result.severity == "error"
    assert result.payload == "DB timeout"


def test_cli_channel_fallback():
    """Test CLI channel as fallback."""
    router = Router(routing_rules=[], default_channel=None)

    result = router.route("Test message", cli_channel="cli.channel")

    assert result.channel == "cli.channel"
    assert result.payload == "Test message"


def test_rule_precedence():
    """Test that first matching rule wins."""
    rules = [
        {"name": "first", "pattern": ".*", "channel": "first"},
        {"name": "second", "pattern": ".*", "channel": "second"},
    ]

    router = Router(routing_rules=rules)

    result = router.route("Test message")
    assert result.channel == "first"  # First match wins


if __name__ == "__main__":
    test_simple_routing()
    test_pattern_matching()
    test_named_groups_templating()
    test_json_extraction()
    test_cli_channel_fallback()
    test_rule_precedence()
    print("✓ All routing tests passed")
