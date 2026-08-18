"""Tests for axis and start position validation.

Covers BL-03.
"""

from __future__ import annotations

import pytest

from common.config import FieldError, validate_config


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


class TestValidateAxisAndStarts:
    """Validate axis origin corner, start index, and agent start positions."""

    def test_axis_start_index_too_high(self, valid_config: dict[str, object]) -> None:
        """axis_start_index > 1 raises FieldError."""
        valid_config["board_and_agents"]["axis_start_index"] = 5
        with pytest.raises(FieldError, match="axis_start_index"):
            validate_config(valid_config)

    def test_axis_start_index_valid(self, valid_config: dict[str, object]) -> None:
        """axis_start_index = 1 is accepted."""
        valid_config["board_and_agents"]["axis_start_index"] = 1
        validate_config(valid_config)

    def test_axis_origin_corner_invalid(self, valid_config: dict[str, object]) -> None:
        """axis_origin_corner with invalid value raises FieldError."""
        valid_config["board_and_agents"]["axis_origin_corner"] = "middle"
        with pytest.raises(FieldError, match="axis_origin_corner"):
            validate_config(valid_config)

    def test_axis_origin_corner_valid(self, valid_config: dict[str, object]) -> None:
        """axis_origin_corner = bottom-right is accepted."""
        valid_config["board_and_agents"]["axis_origin_corner"] = "bottom-right"
        validate_config(valid_config)

    def test_thief_start_out_of_bounds(self, valid_config: dict[str, object]) -> None:
        """thief_start with coordinates >= grid_size raises FieldError."""
        valid_config["board_and_agents"]["thief_start"] = [9, 9]
        with pytest.raises(FieldError, match="thief_start"):
            validate_config(valid_config)

    def test_thief_start_valid_larger_grid(self, valid_config: dict[str, object]) -> None:
        """thief_start = [4, 4] with grid_size = 8 is accepted."""
        valid_config["board_and_agents"]["grid_size"] = 8
        valid_config["board_and_agents"]["thief_start"] = [4, 4]
        validate_config(valid_config)

    def test_cop_start_out_of_bounds(self, valid_config: dict[str, object]) -> None:
        """cop_start with coordinates >= grid_size raises FieldError."""
        valid_config["board_and_agents"]["cop_start"] = [9, 9]
        with pytest.raises(FieldError, match="cop_start"):
            validate_config(valid_config)

    def test_same_start_positions(self, valid_config: dict[str, object]) -> None:
        """thief_start == cop_start raises FieldError."""
        valid_config["board_and_agents"]["thief_start"] = [3, 3]
        valid_config["board_and_agents"]["cop_start"] = [3, 3]
        with pytest.raises(FieldError, match="thief_start and board_and_agents.cop_start"):
            validate_config(valid_config)

    def test_thief_start_short_list(self, valid_config: dict[str, object]) -> None:
        """thief_start with only 1 element raises FieldError."""
        valid_config["board_and_agents"]["thief_start"] = [3]
        with pytest.raises(FieldError, match="thief_start"):
            validate_config(valid_config)

    def test_thief_start_string(self, valid_config: dict[str, object]) -> None:
        """thief_start as string raises FieldError."""
        valid_config["board_and_agents"]["thief_start"] = "3,3"
        with pytest.raises(FieldError, match="thief_start"):
            validate_config(valid_config)

    def test_axis_start_index_bool(self, valid_config: dict[str, object]) -> None:
        """axis_start_index as bool raises FieldError."""
        valid_config["board_and_agents"]["axis_start_index"] = True
        with pytest.raises(FieldError, match="axis_start_index"):
            validate_config(valid_config)

    def test_start_coord_bool(self, valid_config: dict[str, object]) -> None:
        """start coordinate as bool raises FieldError."""
        valid_config["board_and_agents"]["thief_start"] = [True, 3]
        with pytest.raises(FieldError, match=r"thief_start\[0\]"):
            validate_config(valid_config)
