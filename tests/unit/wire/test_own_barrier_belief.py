"""MEDIUM-4: this peer's OWN barrier is excluded from the belief board.

``observe_opponent`` already excludes a barrier the *opponent* declares, but a barrier the
Police itself places never reached the belief: the grid kept assigning probability mass to a
cell the thief provably cannot occupy, and every diffusion spread more mass back into it.
The exclusion belongs immediately after the domain placement succeeds — ``place_own_barrier``
raises ``IllegalMoveError`` before it mutates, so a refused placement must leave the belief
byte-for-byte as it was rather than excluding a cell the board never got.
"""

from __future__ import annotations

import pytest

from common.domain.rules import IllegalMoveError
from common.domain.scoring import Role
from police_peer.strategy.decision import Decision
from police_peer.wire.brain import BrainDrivenEngine

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}


class _ScriptedBrain:
    """A brain seam that always asks for one fixed barrier cell."""

    def __init__(self, barrier_cell: tuple[int, int]) -> None:
        self._barrier_cell = barrier_cell

    def reset(self, position: tuple[int, int]) -> None:
        return None

    def note_evidence(self, field: dict[str, float]) -> None:
        return None

    def decide(self, engine: object, belief: object, hint: str, arena: str) -> Decision:
        return Decision(action="STAY", barrier_cell=self._barrier_cell, hint="holding")


def _started_engine() -> BrainDrivenEngine:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, terms=_TERMS, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    return engine


def _neighbour_target(engine: BrainDrivenEngine) -> tuple[int, int]:
    """A legal barrier target that is NOT the cop's own cell.

    The cop's own cell is already excluded every half-turn by ``apply_half_turn``, so using
    it would let this test pass on that unrelated exclusion instead of on MEDIUM-4.
    """
    game = engine._session.engine
    return next(cell for cell in game.barrier_targets() if cell != game.position)


def _belief_snapshot(engine: BrainDrivenEngine) -> tuple:
    belief = engine._belief
    return ([row[:] for row in belief.as_matrix()], set(belief.allowed_cells))


def _half_turn(step: int) -> dict:
    return {"step": step, "sender": "thief", "hint": "", "smell_grid": {"3,3": 0.4}}


def test_own_barrier_is_zeroed_and_removed_from_allowed_cells() -> None:
    engine = _started_engine()
    cell = _neighbour_target(engine)
    engine._brain = _ScriptedBrain(cell)

    result = engine.decide()

    assert result["barrier_placed"] == list(cell)
    assert engine._session.engine.barriers == [cell]
    assert engine._session.engine.barriers_placed == 1
    assert engine._belief.prob(cell) == 0.0
    # allowed_cells is a PROPERTY, not a method — a truthiness check on the bound method
    # would silently pass even while the cell stayed allowed.
    assert cell not in engine._belief.allowed_cells


def test_own_barrier_stays_excluded_across_six_further_half_turns() -> None:
    """Diffusion must never leak mass back onto a cell the thief cannot enter."""
    engine = _started_engine()
    cell = _neighbour_target(engine)
    engine._brain = _ScriptedBrain(cell)
    engine.decide()

    for step in range(1, 7):
        engine.observe_opponent(_half_turn(step))
        engine._belief.diffuse()
        assert engine._belief.prob(cell) == 0.0, f"mass leaked back at half-turn {step}"
        assert cell not in engine._belief.allowed_cells

    assert sum(sum(row) for row in engine._belief.as_matrix()) == pytest.approx(1.0)


def test_failed_placement_leaves_the_belief_untouched() -> None:
    """An illegal barrier target raises before it mutates — belief must not pre-exclude it."""
    engine = _started_engine()
    illegal = (6, 6)  # far from the cop's (0, 0) start: never a legal barrier target
    assert illegal not in engine._session.engine.barrier_targets()
    engine._brain = _ScriptedBrain(illegal)
    before = _belief_snapshot(engine)

    with pytest.raises(IllegalMoveError):
        engine.decide()

    assert _belief_snapshot(engine) == before
    assert engine._belief.prob(illegal) > 0.0
    assert illegal in engine._belief.allowed_cells
    assert engine._session.engine.barriers == []
    assert engine._session.engine.barriers_placed == 0
