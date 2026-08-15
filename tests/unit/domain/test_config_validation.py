"""Tests for config field and fixed-value validation.

Covers BL-04, BL-05.
"""

from __future__ import annotations

import pytest

from common.config import FieldError, FixedValueError, validate_config


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


class TestValidateFields:
    """BL-05: all required fields must be present."""

    def test_missing_field(self, valid_config: dict[str, object]) -> None:
        """BL-05: missing required field raises FieldError."""
        del valid_config["board_and_agents"]["grid_size"]
        with pytest.raises(FieldError, match="grid_size"):
            validate_config(valid_config)

    def test_unknown_field(self, valid_config: dict[str, object]) -> None:
        """BL-05: unknown field raises FieldError."""
        valid_config["board_and_agents"]["unknown_field"] = 1
        with pytest.raises(FieldError, match="unknown_field"):
            validate_config(valid_config)


class TestValidateFixedValues:
    """BL-04: fixed values are immutable."""

    def test_move_set_changed(self, valid_config: dict[str, object]) -> None:
        """BL-04: changed move_set raises FixedValueError."""
        valid_config["movement_and_barriers"]["move_set"] = ["N", "S"]
        with pytest.raises(FixedValueError, match="move_set"):
            validate_config(valid_config)

    def test_capture_cop_changed(self, valid_config: dict[str, object]) -> None:
        """BL-04: changed scoring.capture_cop raises FixedValueError."""
        valid_config["scoring"]["capture_cop"] = 25
        with pytest.raises(FixedValueError, match="capture_cop"):
            validate_config(valid_config)

    def test_technical_loss_changed(self, valid_config: dict[str, object]) -> None:
        """BL-04: changed scoring.technical_loss raises FixedValueError."""
        valid_config["scoring"]["technical_loss"] = 1
        with pytest.raises(FixedValueError, match="technical_loss"):
            validate_config(valid_config)
