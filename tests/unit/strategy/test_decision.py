"""Decision contract tests.

TC-P01: construction & smoke — build from config; decide() returns a Decision
whose action is in state.legal_moves() and whose barrier_cell is None or (when
set) in state.barrier_targets() with action == "STAY".
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from police_peer.strategy import Decision, resolve_brain


class TestDecisionConstruction:
    """TC-P01: Decision construction and field invariants."""

    def test_default_values(self) -> None:
        d = Decision(action="MOVE:N")
        assert d.barrier_cell is None
        assert d.hint == ""
        assert d.verdict == "truth"
        assert d.fallback is False
        assert d.reasoning == ""
        assert d.prompt_text == ""
        assert d.response_seconds == 0.0

    def test_immutable(self) -> None:
        d = Decision(action="MOVE:S", hint="hello", verdict="lie", fallback=True)
        with pytest.raises(AttributeError):
            d.action = "STAY"  # type: ignore[misc]

    def test_serializable_projection(self) -> None:
        d = Decision(action="MOVE:N", barrier_cell=None, hint="here", verdict="truth")
        assert d.action == "MOVE:N"
        assert d.barrier_cell is None
        assert d.hint == "here"
        assert d.verdict == "truth"


class TestSmoke:
    """TC-P01 smoke: build the brain from config; decide() returns legal action."""

    def test_brain_constructible(self) -> None:
        config: dict = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.POLICE)
        assert brain is not None

    def test_decide_returns_legal_action(self) -> None:
        config: dict = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.POLICE)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(0, 0))
        belief = _UniformBelief(board)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action in engine.legal_moves()
        # barrier_cell is either None or a legal barrier target with action == "STAY"
        if decision.barrier_cell is not None:
            assert decision.action == "STAY"
            assert decision.barrier_cell in engine.barrier_targets()

    def test_barrier_cell_legal_when_set(self) -> None:
        """When barrier_cell is set, action must be STAY and cell must be a legal barrier target."""
        config: dict = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.POLICE)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(3, 3))
        belief = _PeakBelief(board, (3, 3))
        decision = brain.decide(engine, belief, "", "New York")
        if decision.barrier_cell is not None:
            assert decision.action == "STAY"
            assert decision.barrier_cell in engine.barrier_targets()


class _UniformBelief:
    """Minimal belief stub: uniform distribution."""

    def __init__(self, board) -> None:
        self._board = board
        self._size = board.size

    def most_likely(self):
        return (0, 0)

    def peak_probability(self) -> float:
        return 1.0 / (self._size * self._size)

    def prob(self, cell):
        return 1.0 / (self._size * self._size)


class _PeakBelief:
    """Belief with a single peak at the given cell."""

    def __init__(self, board, peak, peak_prob=0.5):
        self._board = board
        self._peak = peak
        self._size = board.size
        self._peak_prob = peak_prob

    def most_likely(self):
        return self._peak

    def peak_probability(self) -> float:
        return self._peak_prob

    def prob(self, cell):
        if cell == self._peak:
            return self._peak_prob
        return 0.01
