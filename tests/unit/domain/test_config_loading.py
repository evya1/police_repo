"""Tests for config loading and section validation.

Covers BL-05, BL-07.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.config import ConfigError, FieldError, load_config, validate_config


@pytest.fixture
def valid_config() -> dict[str, object]:
    """Return a minimal valid config dict."""
    return {
        "schema_version": "1.2",
        "agreed_between": ["police", "thief"],
        "board_and_agents": {
            "grid_size": 7,
            "num_agents": 2,
            "thief_start": [3, 3],
            "cop_start": [0, 0],
            "axis_origin_corner": "top-left",
            "axis_start_index": 0,
        },
        "movement_and_barriers": {
            "move_set": ["N", "S", "E", "W", "STAY"],
            "max_barriers": 14,
            "max_moves": 35,
            "survival_threshold": 35,
        },
        "scoring": {
            "capture_cop": 20,
            "capture_thief": 5,
            "survival_cop": 5,
            "survival_thief": 10,
            "tie_score": 2,
            "technical_loss": 0,
        },
        "world": {"map_area": "New York", "hint_max_words": 15},
        "pheromones": {
            "pheromone_center_intensity": 0.9,
            "pheromone_decay": 0.10,
            "pheromone_grid_size": 5,
        },
        "network_and_league": {
            "response_timeout_sec": 30,
            "watchdog_timeout_sec": 60,
            "num_games": 1,
            "diversity_reward": 10,
            "min_games_to_pass": 2,
            "max_games_per_team": 10,
            "token_budget_per_series": 200000,
        },
        "rate_limiter_gatekeeper": {
            "requests_per_minute": 30,
            "concurrent_requests": 2,
            "retry_backoff_sec": 5,
            "max_retries": 3,
            "queue_depth": 100,
        },
    }


class TestLoadConfig:
    """BL-05: fixed field names, BL-07: overlay."""

    def test_load_valid_config(self, valid_config: dict[str, object], tmp_path: Path) -> None:
        """BL-05: valid config loads without error."""
        config_file = tmp_path / "game.json"
        config_file.write_text(json.dumps(valid_config))
        result = load_config(config_file)
        assert result == valid_config

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Config file not found raises ConfigError."""
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "missing.json")


class TestValidateSections:
    """BL-05: all required sections must be present."""

    def test_missing_section(self, valid_config: dict[str, object]) -> None:
        """BL-05: missing section raises FieldError."""
        del valid_config["world"]
        with pytest.raises(FieldError, match="Missing required sections"):
            validate_config(valid_config)

    def test_unknown_section(self, valid_config: dict[str, object]) -> None:
        """BL-05: unknown section raises FieldError."""
        valid_config["unknown_section"] = {}
        with pytest.raises(FieldError, match="Unknown sections"):
            validate_config(valid_config)
