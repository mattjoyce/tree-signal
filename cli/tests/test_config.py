"""Basic tests for config loading."""

import json
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tree_signal_cli.config import (
    TOMLLoader,
    JSONLoader,
    get_default_config,
    load_config,
    merge_configs,
)


def test_toml_loader():
    """Test TOML config loading."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[api]
url = "http://test:8013"
key = "test-key"

[defaults]
channel = "test.logs"
""")
        f.flush()
        path = Path(f.name)

    try:
        loader = TOMLLoader()
        assert loader.can_load(path)

        config = loader.load(path)
        assert config["api"]["url"] == "http://test:8013"
        assert config["api"]["key"] == "test-key"
        assert config["defaults"]["channel"] == "test.logs"
    finally:
        path.unlink()


def test_json_loader():
    """Test JSON config loading."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "api": {"url": "http://test:8013"},
            "defaults": {"channel": "test"}
        }, f)
        f.flush()
        path = Path(f.name)

    try:
        loader = JSONLoader()
        assert loader.can_load(path)

        config = loader.load(path)
        assert config["api"]["url"] == "http://test:8013"
        assert config["defaults"]["channel"] == "test"
    finally:
        path.unlink()


def test_merge_configs():
    """Test config merging with precedence."""
    base = {
        "api": {"url": "http://localhost:8013", "key": None},
        "defaults": {"channel": "default"},
    }

    override = {
        "api": {"key": "secret"},
        "defaults": {"channel": "override"},
    }

    result = merge_configs(base, override)

    # Override wins
    assert result["api"]["key"] == "secret"
    assert result["defaults"]["channel"] == "override"

    # Base value preserved if not overridden
    assert result["api"]["url"] == "http://localhost:8013"


def test_default_config():
    """Test default config has required keys."""
    config = get_default_config()

    assert "api" in config
    assert "defaults" in config
    assert "performance" in config
    assert "retry" in config
    assert "logging" in config
    assert "routing" in config

    assert config["api"]["url"] == "http://localhost:8013"
    assert config["defaults"]["severity"] == "info"
    assert config["performance"]["batch_size"] == 1


if __name__ == "__main__":
    test_toml_loader()
    test_json_loader()
    test_merge_configs()
    test_default_config()
    print("✓ All config tests passed")
