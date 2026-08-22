"""Failing-first test: brain/belief/session/trail/claims are fresh per sub-game.

Item 9 of the repair task's required tests.
"""

from __future__ import annotations

from common.domain.scoring import Role
from police_peer.wire.brain import BrainDrivenEngine

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}


def test_pending_claim_and_terminal_state_do_not_leak_across_subgames() -> None:
    # THIEF sub-games (stand-in fallback on this package) are the side that
    # actually receives capture_claim messages (police-only, PRD FR-P5).
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, config={})
    engine.start_subgame(2, Role.THIEF, terms=_TERMS)
    engine.observe_opponent({"capture_claim": [0, 0], "smell_grid": {}, "hint": ""})
    assert engine._session.pending_claim is not None

    engine.start_subgame(4, Role.THIEF, terms=_TERMS)
    assert engine._session.pending_claim is None
    assert engine._session.pending_claim_position is None
    assert engine._session.thief_caught is False
    assert engine._session.opponent_terminal is None


def test_belief_and_brain_reset_to_uniform_each_police_subgame() -> None:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    engine.observe_opponent({"smell_grid": {"6,6": 0.9}, "hint": ""})
    engine.decide()
    assert engine._belief.peak_probability() > 1.0 / 49.0

    engine.start_subgame(3, Role.POLICE, terms=_TERMS)
    assert engine._belief.peak_probability() < 0.05
    assert engine._brain.last_field == {}
    assert engine._brain.visited == {engine._session.engine.position}


def test_trail_state_does_not_carry_across_subgames() -> None:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    first_trail = engine._session.trail
    engine.decide()
    assert first_trail.field

    engine.start_subgame(3, Role.POLICE, terms=_TERMS)
    second_trail = engine._session.trail
    assert second_trail is not first_trail
    assert second_trail.field == {}
