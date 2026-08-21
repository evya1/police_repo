"""Unit tests for the police_peer SDK facade."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.config import ConfigError
from common.domain.scoring import Role
from police_peer import __version__, create_peer, validate_startup_config
from police_peer.sdk import SUPPORTED_SCHEMA_VERSIONS, Budgets


@pytest.fixture
def sample_config() -> dict[str, object]:
    return {
        "schema_version": "1.2",
        "agreed_between": ["police-test", "thief-test"],
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
        "world": {
            "map_area": "New York",
            "hint_max_words": 15,
        },
        "pheromones": {
            "pheromone_center_intensity": 0.9,
            "pheromone_decay": 0.1,
            "pheromone_grid_size": 5,
        },
        "network_and_league": {
            "response_timeout_sec": 30,
            "watchdog_timeout_sec": 60,
            "num_games": 6,
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


def test_version_present() -> None:
    assert __version__ == "1.0.0"
    assert "1.2" in SUPPORTED_SCHEMA_VERSIONS


def test_validate_startup_config_valid(sample_config: dict[str, object]) -> None:
    validate_startup_config(sample_config)


def test_validate_startup_config_missing_version(sample_config: dict[str, object]) -> None:
    del sample_config["schema_version"]
    with pytest.raises(ConfigError, match="Missing required field 'schema_version'"):
        validate_startup_config(sample_config)


def test_validate_startup_config_unsupported_version(sample_config: dict[str, object]) -> None:
    sample_config["schema_version"] = "99.0"
    with pytest.raises(ConfigError, match="Unsupported schema_version"):
        validate_startup_config(sample_config)


def test_validate_startup_config_not_dict() -> None:
    with pytest.raises(ConfigError, match="must be a dictionary"):
        validate_startup_config("not a dict")  # type: ignore[arg-type]


def test_create_peer_from_file(tmp_path: Path, sample_config: dict[str, object]) -> None:
    cfg_file = tmp_path / "game.json"
    cfg_file.write_text(json.dumps(sample_config), encoding="utf-8")
    peer = create_peer(cfg_file, role=Role.POLICE, group_id="police-test")
    assert peer is not None
    assert peer.config.natural_role == Role.POLICE
    assert peer.config.terms["num_games"] == 6


def test_create_peer_from_dict(sample_config: dict[str, object]) -> None:
    peer = create_peer(sample_config, role=Role.POLICE)
    assert peer is not None
    assert peer.config.terms["max_steps"] == 35


def test_create_peer_divergent_contract_refusal(sample_config: dict[str, object]) -> None:
    sample_config["movement_and_barriers"]["max_moves"] = 40  # type: ignore[index]
    sample_config["movement_and_barriers"]["survival_threshold"] = 35  # type: ignore[index]
    with pytest.raises(ConfigError, match="Operational contract violation"):
        create_peer(sample_config, role=Role.POLICE)


def test_create_peer_custom_budgets(sample_config: dict[str, object]) -> None:
    budgets = Budgets(turn_timeout=10.0, connect_timeout=5.0, poll_interval=0.001)
    peer = create_peer(sample_config, budgets=budgets)
    assert peer.config.budgets.turn_timeout == 10.0
