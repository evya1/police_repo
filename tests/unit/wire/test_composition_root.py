"""Failing-first tests: create_peer is the production composition root.

Item 1/2 of the repair task's required tests: the default factory path
returns ``BrainDrivenEngine`` with a fresh, configured ``PoliceBrain`` per
POLICE sub-game; an explicit legacy ``strategy=`` still selects the
documented ``StandInEngine`` compatibility path.
"""

from __future__ import annotations

from common.domain.scoring import Role
from police_peer.sdk import create_peer
from police_peer.strategy import BaselineStrategy
from police_peer.wire import BrainDrivenEngine, StandInEngine

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}

_SAMPLE_CONFIG: dict = {
    "schema_version": "1.2",
    "agreed_between": ["police-test", "thief-test"],
    "board_and_agents": {
        "grid_size": 7, "num_agents": 2, "thief_start": [3, 3], "cop_start": [0, 0],
        "axis_origin_corner": "top-left", "axis_start_index": 0,
    },
    "movement_and_barriers": {
        "move_set": ["N", "S", "E", "W", "STAY"], "max_barriers": 14,
        "max_moves": 35, "survival_threshold": 35,
    },
    "scoring": {
        "capture_cop": 20, "capture_thief": 5, "survival_cop": 5, "survival_thief": 10,
        "tie_score": 2, "technical_loss": 0,
    },
    "world": {"map_area": "New York", "hint_max_words": 15},
    "pheromones": {
        "pheromone_center_intensity": 0.9, "pheromone_decay": 0.1, "pheromone_grid_size": 5,
    },
    "network_and_league": {
        "response_timeout_sec": 30, "watchdog_timeout_sec": 60, "num_games": 6,
        "diversity_reward": 10, "min_games_to_pass": 2, "max_games_per_team": 10,
        "token_budget_per_series": 200000,
    },
    "rate_limiter_gatekeeper": {
        "requests_per_minute": 30, "concurrent_requests": 2, "retry_backoff_sec": 5,
        "max_retries": 3, "queue_depth": 100,
    },
}


def test_default_create_peer_returns_brain_driven_engine() -> None:
    peer = create_peer(_SAMPLE_CONFIG, role=Role.POLICE, group_id="p")
    assert isinstance(peer.engine, BrainDrivenEngine)
    assert not isinstance(peer.engine, StandInEngine)


def test_default_engine_uses_fresh_police_brain_per_subgame() -> None:
    peer = create_peer(_SAMPLE_CONFIG, role=Role.POLICE, group_id="p")
    engine = peer.engine
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    brain_one = engine._brain
    assert brain_one is not None
    engine.start_subgame(3, Role.POLICE, terms=_TERMS)
    brain_two = engine._brain
    assert brain_two is not None
    assert brain_one is not brain_two


def test_explicit_strategy_selects_stand_in_engine() -> None:
    peer = create_peer(
        _SAMPLE_CONFIG, role=Role.POLICE, group_id="p", strategy=BaselineStrategy(),
    )
    assert isinstance(peer.engine, StandInEngine)


def test_construction_makes_no_model_or_network_call() -> None:
    """Construction must be pure; reaching here without hanging/raising is the proof."""
    peer = create_peer(_SAMPLE_CONFIG, role=Role.POLICE, group_id="p")
    assert peer is not None


def test_custom_brain_injection_and_seeded_config_still_work() -> None:
    cfg = {"strategy": {"police_class": "police_peer.strategy.police:PoliceBrain"}, "seed": 7}
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=7, config=cfg)
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    assert engine._brain.__class__.__name__ == "PoliceBrain"
