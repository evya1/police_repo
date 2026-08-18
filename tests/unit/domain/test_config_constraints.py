"""Tests for config minimums and agent count constraints.

Covers BL-02, BL-04.
"""

from __future__ import annotations

import pytest

from common.config import ConfigError, MinimumError, validate_config


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


class TestValidateMinimums:
    """BL-04: minimum values cannot be lowered."""

    def test_grid_size_below_minimum(self, valid_config: dict[str, object]) -> None:
        """BL-04: grid_size < 7 raises MinimumError."""
        valid_config["board_and_agents"]["grid_size"] = 6
        with pytest.raises(MinimumError, match="grid_size"):
            validate_config(valid_config)

    def test_grid_size_at_minimum(self, valid_config: dict[str, object]) -> None:
        """BL-04: grid_size = 7 is accepted."""
        valid_config["board_and_agents"]["grid_size"] = 7
        validate_config(valid_config)

    def test_grid_size_above_minimum(self, valid_config: dict[str, object]) -> None:
        """BL-04: grid_size > 7 is accepted."""
        valid_config["board_and_agents"]["grid_size"] = 9
        validate_config(valid_config)

    def test_max_barriers_below_minimum(self, valid_config: dict[str, object]) -> None:
        """BL-04: max_barriers < 14 raises MinimumError."""
        valid_config["movement_and_barriers"]["max_barriers"] = 10
        with pytest.raises(MinimumError, match="max_barriers"):
            validate_config(valid_config)

    def test_max_moves_below_minimum(self, valid_config: dict[str, object]) -> None:
        """BL-04: max_moves < 35 raises MinimumError."""
        valid_config["movement_and_barriers"]["max_moves"] = 30
        with pytest.raises(MinimumError, match="max_moves"):
            validate_config(valid_config)

    def test_survival_threshold_below_minimum(self, valid_config: dict[str, object]) -> None:
        """BL-04: survival_threshold < 35 raises MinimumError."""
        valid_config["movement_and_barriers"]["survival_threshold"] = 30
        with pytest.raises(MinimumError, match="survival_threshold"):
            validate_config(valid_config)

    def test_minimums_raised_by_agreement(self, valid_config: dict[str, object]) -> None:
        """BL-04: minimums may be raised by agreement."""
        valid_config["board_and_agents"]["grid_size"] = 9
        valid_config["movement_and_barriers"]["max_barriers"] = 20
        valid_config["movement_and_barriers"]["max_moves"] = 50
        valid_config["movement_and_barriers"]["survival_threshold"] = 50
        validate_config(valid_config)


class TestValidateNumAgents:
    """BL-02: number of agents must be exactly 2."""

    def test_num_agents_not_two(self, valid_config: dict[str, object]) -> None:
        """BL-02: num_agents != 2 raises ConfigError."""
        valid_config["board_and_agents"]["num_agents"] = 3
        with pytest.raises(ConfigError, match="num_agents"):
            validate_config(valid_config)

    def test_num_agents_is_two(self, valid_config: dict[str, object]) -> None:
        """BL-02: num_agents = 2 is accepted."""
        valid_config["board_and_agents"]["num_agents"] = 2
        validate_config(valid_config)
