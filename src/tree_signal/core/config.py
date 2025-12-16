"""Server-side configuration management with TOML support."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ClientColors:
    """Client color palette configuration."""

    assignment_mode: str = "increment"
    inheritance_mode: str = "unique"
    palette: Optional[list[str]] = None


@dataclass
class ClientUI:
    """Client UI configuration."""

    min_panel_size: float = 5.0
    panel_gap: float = 0.6
    font_family: str = "Fira Code, monospace"
    show_timestamps: bool = True
    timestamp_format: str = "locale"


@dataclass
class ClientConfig:
    """Client-side configuration served to dashboard."""

    api_base_url: str = ""
    refresh_interval_ms: int = 5000
    show_debug: bool = False
    version: str = "0.2.0"
    colors: ClientColors = field(default_factory=ClientColors)
    ui: ClientUI = field(default_factory=ClientUI)


@dataclass
class DecayConfig:
    """Decay timing configuration."""

    hold_seconds: float = 30.0
    decay_seconds: float = 10.0


@dataclass
class HistoryConfig:
    """Message history configuration."""

    max_messages: int = 100


@dataclass
class ServerConfig:
    """Server runtime configuration."""

    host: str = "0.0.0.0"
    port: int = 8013


@dataclass
class CleanupConfig:
    """Cleanup task configuration."""

    interval_seconds: float = 60.0


@dataclass
class TreeSignalConfig:
    """Root configuration for Tree Signal."""

    decay: DecayConfig = field(default_factory=DecayConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    cleanup: CleanupConfig = field(default_factory=CleanupConfig)
    client: ClientConfig = field(default_factory=ClientConfig)


def find_config_file() -> Path | None:
    """
    Find configuration file using precedence order.

    1. TREE_SIGNAL_CONFIG environment variable
    2. /app/data/config.toml (Docker mount)
    3. ./config.toml (current directory)
    4. ~/.config/tree-signal/config.toml (user config)

    Returns Path if found, None if no config exists.
    """
    # 1. Environment variable (must exist)
    env_path = os.getenv("TREE_SIGNAL_CONFIG")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # 2. Docker mount location
    docker_path = Path("/app/data/config.toml")
    if docker_path.exists():
        return docker_path

    # 3. Current directory
    local_path = Path("./config.toml")
    if local_path.exists():
        return local_path

    # 4. User config directory
    user_config = Path.home() / ".config" / "tree-signal" / "config.toml"
    if user_config.exists():
        return user_config

    return None


def load_toml_config(config_path: Path) -> dict:
    """Load configuration from TOML file."""
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def merge_dict(base: dict, override: dict) -> dict:
    """Deep merge two dicts. Override takes precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def dict_to_client_colors(data: dict) -> ClientColors:
    """Convert dict to ClientColors dataclass."""
    return ClientColors(
        assignment_mode=data.get("assignment_mode", "increment"),
        inheritance_mode=data.get("inheritance_mode", "unique"),
        palette=data.get("palette"),
    )


def dict_to_client_ui(data: dict) -> ClientUI:
    """Convert dict to ClientUI dataclass."""
    return ClientUI(
        min_panel_size=data.get("min_panel_size", 5.0),
        panel_gap=data.get("panel_gap", 0.6),
        font_family=data.get("font_family", "Fira Code, monospace"),
        show_timestamps=data.get("show_timestamps", True),
        timestamp_format=data.get("timestamp_format", "locale"),
    )


def dict_to_client_config(data: dict) -> ClientConfig:
    """Convert dict to ClientConfig dataclass."""
    colors_data = data.get("colors", {})
    ui_data = data.get("ui", {})

    return ClientConfig(
        api_base_url=data.get("api_base_url", ""),
        refresh_interval_ms=data.get("refresh_interval_ms", 5000),
        show_debug=data.get("show_debug", False),
        version=data.get("version", "0.2.0"),
        colors=dict_to_client_colors(colors_data),
        ui=dict_to_client_ui(ui_data),
    )


def dict_to_config(data: dict) -> TreeSignalConfig:
    """Convert dict to TreeSignalConfig dataclass."""
    decay_data = data.get("decay", {})
    history_data = data.get("history", {})
    server_data = data.get("server", {})
    cleanup_data = data.get("cleanup", {})
    client_data = data.get("client", {})

    return TreeSignalConfig(
        decay=DecayConfig(
            hold_seconds=decay_data.get("hold_seconds", 30.0),
            decay_seconds=decay_data.get("decay_seconds", 10.0),
        ),
        history=HistoryConfig(max_messages=history_data.get("max_messages", 100)),
        server=ServerConfig(
            host=server_data.get("host", "0.0.0.0"), port=server_data.get("port", 8013)
        ),
        cleanup=CleanupConfig(interval_seconds=cleanup_data.get("interval_seconds", 60.0)),
        client=dict_to_client_config(client_data),
    )


def load_config() -> TreeSignalConfig:
    """
    Load configuration from file or use defaults.

    Configuration precedence:
    1. Config file (if found)
    2. Environment variables (for specific overrides)
    3. Built-in defaults
    """
    # Start with defaults
    config = TreeSignalConfig()

    # Try to load from file
    config_path = find_config_file()
    if config_path:
        try:
            toml_data = load_toml_config(config_path)
            config = dict_to_config(toml_data)
        except Exception as e:
            # Log error but continue with defaults
            print(f"Warning: Failed to load config from {config_path}: {e}")

    # Environment variable overrides (for backward compatibility)
    color_mode = os.getenv("COLOR_ASSIGNMENT_MODE")
    if color_mode:
        config.client.colors.assignment_mode = color_mode

    color_inheritance = os.getenv("COLOR_INHERITANCE_MODE")
    if color_inheritance:
        config.client.colors.inheritance_mode = color_inheritance

    return config


# Global config instance (loaded once at startup)
_config: Optional[TreeSignalConfig] = None


def get_config() -> TreeSignalConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> TreeSignalConfig:
    """Reload configuration from disk."""
    global _config
    _config = load_config()
    return _config
