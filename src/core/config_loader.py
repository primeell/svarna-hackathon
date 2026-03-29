"""
Project SVARNA — YAML Config Loader
=====================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger


def load_config(config_path: str = "AgentConfig.yaml") -> dict[str, Any]:
    """
    Load and return the YAML configuration.

    Args:
        config_path: Path to the AgentConfig.yaml file.

    Returns:
        Parsed configuration dictionary.
    """
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Config file not found: {path}. Using defaults.")
        return _default_config()

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info(f"Loaded config from {path}")
    return config


def get_agent_config(config: dict, agent_name: str) -> dict[str, Any]:
    """Extract a specific agent's configuration."""
    agents = config.get("agents", {})
    if agent_name not in agents:
        raise KeyError(f"Agent '{agent_name}' not found in config")
    return agents[agent_name]


def _default_config() -> dict[str, Any]:
    """Minimal fallback configuration."""
    return {
        "system": {
            "project_name": "SVARNA",
            "version": "0.1.0",
            "log_level": "INFO",
        },
        "agents": {},
        "blackboard": {
            "backend": "sqlite",
            "path": "data/svarna_blackboard.db",
        },
    }
