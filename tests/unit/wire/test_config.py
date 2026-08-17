"""Tests for wire/config.py — PrivateConfig + PeerConfig assembly.

CFG-003: JSON overlays TOML on conflict; TOML may add local-only keys.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.police_peer.wire.config import (
    PrivateConfig,
    assemble_peer_config,
    build_peer_config,
    load_private,
    verify_terms_closed,
)


def _write_valid_json(path: Path) -> None:
    data = {
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
    path.write_text(json.dumps(data), encoding="utf-8")


class TestPrivateConfig:
    """Tests for PrivateConfig dataclass."""

    def test_defaults(self) -> None:
        cfg = PrivateConfig()
        assert cfg.min_center_intensity == 0.5
        assert cfg.group_id == ""
        assert cfg.seed == 0
        assert cfg.budgets == {}

    def test_custom_values(self) -> None:
        cfg = PrivateConfig(min_center_intensity=0.7, group_id="team-x", seed=42)
        assert cfg.min_center_intensity == 0.7
        assert cfg.group_id == "team-x"
        assert cfg.seed == 42


class TestLoadPrivate:
    """Tests for load_private — reads game.toml."""

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        result = load_private(tmp_path / "missing.toml")
        assert isinstance(result, PrivateConfig)
        assert result.min_center_intensity == 0.5

    def test_reads_min_center_intensity(self, tmp_path: Path) -> None:
        toml = tmp_path / "game.toml"
        toml.write_text('min_center_intensity = 0.7\n', encoding="utf-8")
        result = load_private(toml)
        assert result.min_center_intensity == 0.7

    def test_reads_group_id(self, tmp_path: Path) -> None:
        toml = tmp_path / "game.toml"
        toml.write_text('group_id = "my-team"\n', encoding="utf-8")
        result = load_private(toml)
        assert result.group_id == "my-team"

    def test_reads_seed(self, tmp_path: Path) -> None:
        toml = tmp_path / "game.toml"
        toml.write_text('seed = 1234\n', encoding="utf-8")
        result = load_private(toml)
        assert result.seed == 1234


class TestBuildPeerConfig:
    """Tests for build_peer_config — JSON + TOML assembly, CFG-003."""

    def test_returns_closed_terms(self, tmp_path: Path) -> None:
        json_path = tmp_path / "game.json"
        _write_valid_json(json_path)
        private = PrivateConfig()
        terms = build_peer_config(json_path, private)
        errors = verify_terms_closed(terms)
        assert errors == []

    def test_num_games_fixed_at_six(self, tmp_path: Path) -> None:
        json_path = tmp_path / "game.json"
        # JSON says num_games=1 (known discrepancy O-2)
        data = {
            "schema_version": "1.2",
            "agreed_between": ["a", "b"],
            "board_and_agents": {
                "grid_size": 7, "num_agents": 2,
                "thief_start": [3, 3], "cop_start": [0, 0],
                "axis_origin_corner": "top-left", "axis_start_index": 0,
            },
            "movement_and_barriers": {
                "move_set": ["N", "S", "E", "W", "STAY"],
                "max_barriers": 14, "max_moves": 35, "survival_threshold": 35,
            },
            "scoring": {
                "capture_cop": 20, "capture_thief": 5,
                "survival_cop": 5, "survival_thief": 10,
                "tie_score": 2, "technical_loss": 0,
            },
            "world": {"map_area": "New York", "hint_max_words": 15},
            "pheromones": {
                "pheromone_center_intensity": 0.9,
                "pheromone_decay": 0.1, "pheromone_grid_size": 5,
            },
            "network_and_league": {
                "response_timeout_sec": 30, "watchdog_timeout_sec": 60,
                "num_games": 1, "diversity_reward": 10,
                "min_games_to_pass": 2, "max_games_per_team": 10,
                "token_budget_per_series": 200000,
            },
            "rate_limiter_gatekeeper": {
                "requests_per_minute": 30, "concurrent_requests": 2,
                "retry_backoff_sec": 5, "max_retries": 3, "queue_depth": 100,
            },
        }
        json_path.write_text(json.dumps(data), encoding="utf-8")
        private = PrivateConfig()
        terms = build_peer_config(json_path, private)
        assert terms["num_games"] == 6

    def test_setting_from_json(self, tmp_path: Path) -> None:
        json_path = tmp_path / "game.json"
        data = {
            "schema_version": "1.2",
            "agreed_between": ["a", "b"],
            "board_and_agents": {
                "grid_size": 7, "num_agents": 2,
                "thief_start": [3, 3], "cop_start": [0, 0],
                "axis_origin_corner": "top-left", "axis_start_index": 0,
            },
            "movement_and_barriers": {
                "move_set": ["N", "S", "E", "W", "STAY"],
                "max_barriers": 14, "max_moves": 35, "survival_threshold": 35,
            },
            "scoring": {
                "capture_cop": 20, "capture_thief": 5,
                "survival_cop": 5, "survival_thief": 10,
                "tie_score": 2, "technical_loss": 0,
            },
            "world": {"map_area": "Haifa", "hint_max_words": 15},
            "pheromones": {
                "pheromone_center_intensity": 0.9,
                "pheromone_decay": 0.1, "pheromone_grid_size": 5,
            },
            "network_and_league": {
                "response_timeout_sec": 30, "watchdog_timeout_sec": 60,
                "num_games": 6, "diversity_reward": 10,
                "min_games_to_pass": 2, "max_games_per_team": 10,
                "token_budget_per_series": 200000,
            },
            "rate_limiter_gatekeeper": {
                "requests_per_minute": 30, "concurrent_requests": 2,
                "retry_backoff_sec": 5, "max_retries": 3, "queue_depth": 100,
            },
        }
        json_path.write_text(json.dumps(data), encoding="utf-8")
        private = PrivateConfig()
        terms = build_peer_config(json_path, private)
        assert terms["setting"] == "Haifa"

    def test_private_min_center_intensity_overrides_default(self, tmp_path: Path) -> None:
        json_path = tmp_path / "game.json"
        _write_valid_json(json_path)
        private = PrivateConfig(min_center_intensity = 0.8)
        terms = build_peer_config(json_path, private)
        assert terms["min_center_intensity"] == 0.8

    def test_private_min_center_intensity_default(self, tmp_path: Path) -> None:
        json_path = tmp_path / "game.json"
        _write_valid_json(json_path)
        private = PrivateConfig()
        terms = build_peer_config(json_path, private)
        assert terms["min_center_intensity"] == 0.5


class TestAssemblePeerConfig:
    """Tests for assemble_peer_config — full PeerConfig assembly."""

    def test_returns_expected_keys(self, tmp_path: Path) -> None:
        json_path = tmp_path / "game.json"
        _write_valid_json(json_path)
        private = PrivateConfig()
        result = assemble_peer_config(json_path, private, "police")
        assert "terms" in result
        assert "natural_role" in result
        assert "seed" in result
        assert "budgets" in result
        assert result["natural_role"] == "police"

    def test_terms_are_closed(self, tmp_path: Path) -> None:
        json_path = tmp_path / "game.json"
        _write_valid_json(json_path)
        private = PrivateConfig()
        result = assemble_peer_config(json_path, private, "police")
        errors = verify_terms_closed(result["terms"])
        assert errors == []

    def test_num_games_overridden(self, tmp_path: Path) -> None:
        data = {
            "schema_version": "1.2",
            "agreed_between": ["a", "b"],
            "board_and_agents": {
                "grid_size": 7, "num_agents": 2,
                "thief_start": [3, 3], "cop_start": [0, 0],
                "axis_origin_corner": "top-left", "axis_start_index": 0,
            },
            "movement_and_barriers": {
                "move_set": ["N", "S", "E", "W", "STAY"],
                "max_barriers": 14, "max_moves": 35, "survival_threshold": 35,
            },
            "scoring": {
                "capture_cop": 20, "capture_thief": 5,
                "survival_cop": 5, "survival_thief": 10,
                "tie_score": 2, "technical_loss": 0,
            },
            "world": {"map_area": "New York", "hint_max_words": 15},
            "pheromones": {
                "pheromone_center_intensity": 0.9,
                "pheromone_decay": 0.1, "pheromone_grid_size": 5,
            },
            "network_and_league": {
                "response_timeout_sec": 30, "watchdog_timeout_sec": 60,
                "num_games": 1, "diversity_reward": 10,
                "min_games_to_pass": 2, "max_games_per_team": 10,
                "token_budget_per_series": 200000,
            },
            "rate_limiter_gatekeeper": {
                "requests_per_minute": 30, "concurrent_requests": 2,
                "retry_backoff_sec": 5, "max_retries": 3, "queue_depth": 100,
            },
        }
        json_path = tmp_path / "game.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")
        private = PrivateConfig()
        result = assemble_peer_config(json_path, private, "thief")
        assert result["terms"]["num_games"] == 6


class TestVerifyTermsClosed:
    """Tests for verify_terms_closed — detects deviations from TERMS_KEYS."""

    def test_no_errors_when_closed(self) -> None:
        from common.transport.terms import TERMS_KEYS
        terms = dict.fromkeys(TERMS_KEYS, 0)
        assert verify_terms_closed(terms) == []

    def test_missing_key_detected(self) -> None:
        from common.transport.terms import TERMS_KEYS
        terms = dict.fromkeys(TERMS_KEYS, 0)
        del terms["num_games"]
        errors = verify_terms_closed(terms)
        assert "num_games" in errors

    def test_extra_key_detected(self) -> None:
        from common.transport.terms import TERMS_KEYS
        terms = dict.fromkeys(TERMS_KEYS, 0)
        terms["extra_key"] = 1
        errors = verify_terms_closed(terms)
        assert "extra_key" in errors

    def test_multiple_errors(self) -> None:
        from common.transport.terms import TERMS_KEYS
        terms = dict.fromkeys(TERMS_KEYS, 0)
        del terms["num_games"]
        terms["extra"] = 1
        errors = verify_terms_closed(terms)
        assert "extra" in errors
        assert "num_games" in errors
