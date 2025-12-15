"""
Configuration loading with support for TOML, JSON, and optional YAML.

Implements a modular loader pattern that tries formats in order of preference.
Config precedence: defaults < config file < environment < CLI args
"""

import json
import tomllib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ConfigLoader(ABC):
    """Abstract base class for configuration loaders."""

    @abstractmethod
    def can_load(self, path: Path) -> bool:
        """Check if this loader can handle the given file path."""
        pass

    @abstractmethod
    def load(self, path: Path) -> dict[str, Any]:
        """Load and parse the configuration file."""
        pass


class TOMLLoader(ConfigLoader):
    """Load TOML configuration files using stdlib tomllib (Python 3.11+)."""

    def can_load(self, path: Path) -> bool:
        return path.suffix == ".toml"

    def load(self, path: Path) -> dict[str, Any]:
        """Load TOML file and return as dict."""
        with open(path, "rb") as f:
            return tomllib.load(f)


class JSONLoader(ConfigLoader):
    """Load JSON configuration files using stdlib json."""

    def can_load(self, path: Path) -> bool:
        return path.suffix == ".json"

    def load(self, path: Path) -> dict[str, Any]:
        """Load JSON file and return as dict."""
        with open(path, "r") as f:
            return json.load(f)


class YAMLLoader(ConfigLoader):
    """Load YAML configuration files (requires PyYAML)."""

    def can_load(self, path: Path) -> bool:
        return path.suffix in (".yaml", ".yml")

    def load(self, path: Path) -> dict[str, Any]:
        """Load YAML file if PyYAML is available."""
        try:
            import yaml
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except ImportError:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")


def find_config_file(explicit_path: str | None = None) -> Path | None:
    """
    Find configuration file using precedence order.

    1. Explicit path (--config argument)
    2. TREE_SIGNAL_CONFIG environment variable
    3. ~/.config/tree-signal/config.{toml,json}
    4. /etc/tree-signal/config.{toml,json}

    Returns Path if found, None if no config exists.
    Raises FileNotFoundError if explicit path doesn't exist.
    """
    import os

    # 1. Explicit path (must exist)
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {explicit_path}")
        return path

    # 2. Environment variable (must exist)
    env_path = os.getenv("TREE_SIGNAL_CONFIG")
    if env_path:
        path = Path(env_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {env_path}")
        return path

    # 3. User config directory (optional)
    user_config_dir = Path.home() / ".config" / "tree-signal"
    for ext in [".toml", ".json"]:
        path = user_config_dir / f"config{ext}"
        if path.exists():
            return path

    # 4. System config directory (optional)
    system_config_dir = Path("/etc/tree-signal")
    for ext in [".toml", ".json"]:
        path = system_config_dir / f"config{ext}"
        if path.exists():
            return path

    return None


def load_config(config_path: Path) -> dict[str, Any]:
    """
    Load configuration from file using appropriate loader.

    Tries loaders in order: TOML, JSON, YAML (if available).
    Raises ValueError if no loader can handle the file.
    """
    loaders = [TOMLLoader(), JSONLoader(), YAMLLoader()]

    for loader in loaders:
        if loader.can_load(config_path):
            try:
                return loader.load(config_path)
            except ImportError:
                # YAML loader failed due to missing PyYAML, try next loader
                continue

    raise ValueError(f"Unsupported config format: {config_path.suffix}")


def get_default_config() -> dict[str, Any]:
    """Return default configuration values."""
    return {
        "api": {
            "url": "http://localhost:8013",
            "key": None,
            "timeout": 5000,
        },
        "defaults": {
            "severity": "info",
            "channel": None,  # Required if no routing matches
        },
        "decay": {
            "hold_seconds": 30.0,  # Duration to hold full weight before decay begins
            "decay_seconds": 10.0,  # Duration to fade from full weight to removal
        },
        "performance": {
            "batch_size": 1,
            "batch_interval": 1000,
            "rate_limit": 0,  # 0 = unlimited
        },
        "retry": {
            "max_attempts": 3,
            "base_delay": 1000,
            "max_delay": 30000,
        },
        "logging": {
            "level": "info",
            "format": "text",
            "quiet": False,
            "debug": False,
            "dry_run": False,
        },
        "routing": [],
        "channels": {},
    }


def merge_configs(base: dict, override: dict) -> dict:
    """
    Deep merge two config dicts. Override takes precedence.

    Used for merging: defaults < config file < env vars < CLI args
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result
