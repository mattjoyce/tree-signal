#!/usr/bin/env python3
"""
Tree Signal CLI - Route log streams to Tree Signal dashboard.

Usage:
    tail -f /var/log/app.log | tree-signal --channel myapp.logs
    journalctl -fu myservice | tree-signal --config production.toml
    docker logs -f container | tree-signal --channel docker.container
"""

import argparse
import os
import signal
import sys
from pathlib import Path

from .config import find_config_file, get_default_config, load_config, merge_configs
from .router import Router
from .sender import MessageSender


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Route log streams to Tree Signal dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tail -f app.log | tree-signal --channel myapp.logs
  journalctl -fu nginx | tree-signal --config prod.toml
  cat /var/log/syslog | tree-signal --channel syslog --severity warning

Config precedence (low to high):
  Built-in defaults → Config file → Environment vars → CLI arguments
        """,
    )

    # Config
    parser.add_argument("--config", metavar="PATH", help="Path to config file (TOML/JSON)")
    parser.add_argument("--no-config", action="store_true", help="Ignore config file, use CLI args only")

    # API settings
    parser.add_argument("-a", "--api", metavar="URL", help="Tree Signal API URL (default: http://localhost:8013)")
    parser.add_argument("-k", "--api-key", metavar="KEY", help="API authentication key (or use TREE_SIGNAL_API_KEY)")

    # Message settings
    parser.add_argument("-c", "--channel", metavar="CHANNEL", help="Target channel path (e.g., myapp.api.auth)")
    parser.add_argument("-s", "--severity", metavar="LEVEL",
                       choices=["debug", "info", "warn", "warning", "error", "critical"],
                       help="Default severity level (API uses: debug|info|warn|error)")

    # Performance
    parser.add_argument("-b", "--batch-size", type=int, metavar="N", help="Batch N messages before sending")
    parser.add_argument("--batch-interval", type=int, metavar="MS", help="Max milliseconds before flushing batch")
    parser.add_argument("-r", "--rate-limit", type=int, metavar="N", help="Max messages per second (0=unlimited)")

    # Retry
    parser.add_argument("--retry", type=int, metavar="COUNT", help="Number of retries on API failure")
    parser.add_argument("--retry-delay", type=int, metavar="MS", help="Base delay between retries (ms)")

    # Logging
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress informational output")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Print messages instead of sending")

    return parser.parse_args()


def build_config(args: argparse.Namespace) -> dict:
    """
    Build final config by merging: defaults < config file < env vars < CLI args.

    Returns complete configuration dict.
    """
    # Start with defaults
    config = get_default_config()

    # Load config file (unless --no-config)
    if not args.no_config:
        try:
            config_path = find_config_file(args.config)
            if config_path:
                file_config = load_config(config_path)
                config = merge_configs(config, file_config)
                if not args.quiet:
                    print(f"[INFO] Loaded config: {config_path}", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
            sys.exit(1)

    # Apply environment variables
    env_overrides = {}
    if os.getenv("TREE_SIGNAL_API_URL"):
        env_overrides.setdefault("api", {})["url"] = os.getenv("TREE_SIGNAL_API_URL")
    if os.getenv("TREE_SIGNAL_API_KEY"):
        env_overrides.setdefault("api", {})["key"] = os.getenv("TREE_SIGNAL_API_KEY")

    if env_overrides:
        config = merge_configs(config, env_overrides)

    # Apply CLI arguments (highest priority)
    cli_overrides = {}

    if args.api:
        cli_overrides.setdefault("api", {})["url"] = args.api
    if args.api_key:
        cli_overrides.setdefault("api", {})["key"] = args.api_key
    if args.channel:
        cli_overrides.setdefault("defaults", {})["channel"] = args.channel
    if args.severity:
        cli_overrides.setdefault("defaults", {})["severity"] = args.severity
    if args.batch_size is not None:
        cli_overrides.setdefault("performance", {})["batch_size"] = args.batch_size
    if args.batch_interval is not None:
        cli_overrides.setdefault("performance", {})["batch_interval"] = args.batch_interval
    if args.rate_limit is not None:
        cli_overrides.setdefault("performance", {})["rate_limit"] = args.rate_limit
    if args.retry is not None:
        cli_overrides.setdefault("retry", {})["max_attempts"] = args.retry
    if args.retry_delay is not None:
        cli_overrides.setdefault("retry", {})["base_delay"] = args.retry_delay
    if args.quiet:
        cli_overrides.setdefault("logging", {})["quiet"] = True
    if args.debug:
        cli_overrides.setdefault("logging", {})["debug"] = True
    if args.dry_run:
        cli_overrides.setdefault("logging", {})["dry_run"] = True

    if cli_overrides:
        config = merge_configs(config, cli_overrides)

    return config


def main() -> int:
    """Main entry point for tree-signal CLI."""
    args = parse_args()
    config = build_config(args)

    # Setup router
    router = Router(
        routing_rules=config.get("routing", []),
        default_channel=config["defaults"].get("channel"),
        default_severity=config["defaults"].get("severity", "info"),
    )

    # Setup sender
    sender = MessageSender(
        api_url=config["api"]["url"],
        api_key=config["api"].get("key"),
        batch_size=config["performance"]["batch_size"],
        batch_interval=config["performance"]["batch_interval"] / 1000.0,  # ms to seconds
        rate_limit=config["performance"]["rate_limit"],
        max_retries=config["retry"]["max_attempts"],
        retry_base_delay=config["retry"]["base_delay"] / 1000.0,  # ms to seconds
        retry_max_delay=config["retry"]["max_delay"] / 1000.0,  # ms to seconds
        timeout=config["api"].get("timeout", 5000) / 1000.0,  # ms to seconds
        dry_run=config["logging"]["dry_run"],
        debug=config["logging"]["debug"],
    )

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        if not config["logging"]["quiet"]:
            print("\n[INFO] Shutting down gracefully...", file=sys.stderr)
        sender.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Read from stdin and route messages
    if not config["logging"]["quiet"]:
        print(f"[INFO] Reading from stdin, routing to {config['api']['url']}", file=sys.stderr)

    try:
        for line in sys.stdin:
            if not line.strip():
                continue  # Skip empty lines

            try:
                result = router.route(line, cli_channel=config["defaults"].get("channel"))
                sender.send(result.channel, result.payload, result.severity)
            except ValueError as e:
                if config["logging"]["debug"]:
                    print(f"[DEBUG] Routing error: {e}", file=sys.stderr)
                continue

    except KeyboardInterrupt:
        pass
    finally:
        sender.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
