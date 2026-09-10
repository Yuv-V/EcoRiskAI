"""Configuration helpers for EcoRiskAI."""

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load the project YAML configuration."""
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    return config


def resolve_project_path(path_value: str | Path) -> Path:
    """Resolve a configured project-relative path to an absolute path."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
