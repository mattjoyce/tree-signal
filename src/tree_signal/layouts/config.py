"""Layout configuration and profile management."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union, cast

import yaml


@dataclass
class LinearLayoutConfig:
    """Configuration for the LinearLayoutGenerator."""

    # Fraction of space for parent panel when it has messages (0.0-1.0)
    parent_fraction: float = 0.15

    # Minimum extent for any panel (prevents invisible tiny panels)
    min_extent: float = 0.02

    # Show/hide parent panels that have no direct messages
    show_empty_parents: bool = True

    # Depth-based parent fraction (optional)
    # If set, parent_fraction decreases with depth
    depth_decay_factor: float = 0.0  # 0 = disabled, e.g., 0.05 = reduce 5% per depth

    # Gap between panels as fraction of canvas (0.0-1.0)
    panel_gap: float = 0.0

    # Color service configuration
    color_assignment_mode: str = "increment"
    color_inheritance_mode: str = "unique"


# Preset layout profiles
LAYOUT_PROFILES: dict[str, LinearLayoutConfig] = {
    "default": LinearLayoutConfig(
        parent_fraction=0.15,
        min_extent=0.02,
        show_empty_parents=True,
        depth_decay_factor=0.0,
        panel_gap=0.0,
    ),
    "compact": LinearLayoutConfig(
        parent_fraction=0.08,
        min_extent=0.01,
        show_empty_parents=False,
        depth_decay_factor=0.02,
        panel_gap=0.0,
    ),
    "spacious": LinearLayoutConfig(
        parent_fraction=0.25,
        min_extent=0.05,
        show_empty_parents=True,
        depth_decay_factor=0.0,
        panel_gap=0.005,
    ),
    "minimal": LinearLayoutConfig(
        parent_fraction=0.05,
        min_extent=0.02,
        show_empty_parents=False,
        depth_decay_factor=0.03,
        panel_gap=0.0,
    ),
    "content-first": LinearLayoutConfig(
        parent_fraction=0.0,
        min_extent=0.03,
        show_empty_parents=False,
        depth_decay_factor=0.0,
        panel_gap=0.0,
    ),
}


def find_layouts_directory() -> Path:
    """Find the layouts directory."""
    # 1. Environment variable
    env_path = os.getenv("TREE_SIGNAL_LAYOUTS")
    if env_path:
        return Path(env_path)

    # 2. /app/data/layouts (Docker mount)
    docker_path = Path("/app/data/layouts")
    if docker_path.exists():
        return docker_path

    # 3. ./layouts (current directory)
    local_path = Path("./layouts")
    if local_path.exists():
        return local_path

    # 4. Package default layouts
    package_path = Path(__file__).parent / "profiles"
    return package_path


def load_layout_profile(name: str) -> LinearLayoutConfig:
    """Load a layout profile by name."""
    # Check preset profiles first
    if name in LAYOUT_PROFILES:
        return LAYOUT_PROFILES[name]

    # Try to load from YAML file
    layouts_dir = find_layouts_directory()
    profile_path = layouts_dir / f"{name}.yaml"

    if profile_path.exists():
        with open(profile_path) as f:
            data = yaml.safe_load(f)
            return _dict_to_config(data)

    # Try JSON too
    json_path = layouts_dir / f"{name}.json"
    if json_path.exists():
        import json

        with open(json_path) as f:
            data = json.load(f)
            return _dict_to_config(data)

    raise ValueError(f"Unknown layout profile: {name}")


def _dict_to_config(data: dict[str, object]) -> LinearLayoutConfig:
    """Convert dict to LinearLayoutConfig."""
    if not data:
        return LinearLayoutConfig()

    def get_float(key: str, default: float) -> float:
        val = data.get(key, default)
        if val is None:
            return default
        return float(cast(Union[str, int, float], val))

    def get_bool(key: str, default: bool) -> bool:
        val = data.get(key, default)
        if val is None:
            return default
        return bool(cast(Union[bool, int], val))

    def get_str(key: str, default: str) -> str:
        val = data.get(key, default)
        if val is None:
            return default
        return str(cast(str, val))

    return LinearLayoutConfig(
        parent_fraction=get_float("parent_fraction", 0.15),
        min_extent=get_float("min_extent", 0.02),
        show_empty_parents=get_bool("show_empty_parents", True),
        depth_decay_factor=get_float("depth_decay_factor", 0.0),
        panel_gap=get_float("panel_gap", 0.0),
        color_assignment_mode=get_str("color_assignment_mode", "increment"),
        color_inheritance_mode=get_str("color_inheritance_mode", "unique"),
    )


def list_available_profiles() -> list[str]:
    """List all available layout profiles."""
    profiles = list(LAYOUT_PROFILES.keys())

    layouts_dir = find_layouts_directory()
    if layouts_dir.exists():
        for f in layouts_dir.iterdir():
            if f.suffix in (".yaml", ".yml", ".json"):
                profile_name = f.stem
                if profile_name not in profiles:
                    profiles.append(profile_name)

    return sorted(profiles)
