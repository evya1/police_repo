"""Tests for TOML overlay merging.

Covers BL-07.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.config import overlay_toml


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


class TestOverlayToml:
    """Tests for overlay_toml merging TOML-only keys."""

    def test_overlay_toml_merges_new_keys(
        self, valid_config: dict[str, object], tmp_path: Path
    ) -> None:
        """TOML-only keys are merged into the config."""
        config_file = tmp_path / "game.json"
        config_file.write_text(json.dumps(valid_config))

        toml_file = tmp_path / "game.toml"
        toml_file.write_text(
            '[strategy]\nthief_class = "x"\n'
            '[board_and_agents]\ngrid_size = 9\n'
            '[movement_and_barriers]\nmax_barriers = 10\n'
        )

        result = overlay_toml(config_file, toml_file)

        # TOML-only keys should be added
        assert result["strategy"]["thief_class"] == "x"
        # JSON values should win on conflicts
        assert result["board_and_agents"]["grid_size"] == 7
        assert result["movement_and_barriers"]["max_barriers"] == 14
