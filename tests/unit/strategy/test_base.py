"""BrainBase phase-order, hint-destination, and visited-discipline tests.

TC-P15 (partial): phase order — move phase completes before hint phase.
TC-P18: visited discipline — starts at {start}, grows only on orthogonal MOVE.
M-03 {#hint_isolation}: the hint is written from the destination of the
ALREADY-SELECTED action and can never feed back into move selection.
"""

from __future__ import annotations

import random

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from police_peer.strategy.base import BrainBase
from police_peer.strategy.hints import HintWriter

_BOXED_IN = [(2, 3), (4, 3), (3, 2), (3, 4)]


class _TestBrain(BrainBase):
    """Minimal brain for testing base discipline: always MOVE:N."""

    def _decide_move(self, state, belief):
        return "MOVE:N", None


class _StayBrain(BrainBase):
    """Chooses STAY with a free choice of moves (no barrier)."""

    def _decide_move(self, state, belief):
        return "STAY", None


class _BarrierBrain(BrainBase):
    """Barrier turn: the barrier forfeits the move (GAME-006)."""

    def _decide_move(self, state, belief):
        return "STAY", (3, 3)


class _UniformBelief:
    def __init__(self, board) -> None:
        self._board = board
        self._size = board.size

    def most_likely(self):
        return (0, 0)

    def peak_probability(self) -> float:
        return 1.0 / (self._size * self._size)


class _SpyWriter:
    """Records the cell the hint phase was handed. Optionally mutates the engine
    afterwards — a late mutation must never retro-change the chosen action.
    """

    def __init__(self, engine=None) -> None:
        self.seen: list = []
        self.engine = engine

    def say(self, position, *, deadline: float | None = None) -> tuple[str, str]:
        self.seen.append(position)
        if self.engine is not None:
            self.engine.position = (0, 0)
        return "spy hint", "truth"


def _setup(brain_cls=_TestBrain, writer=None, barriers=None):
    """(brain, engine, belief, writer) — POLICE at (3, 3) on a 7x7 board."""
    rng = random.Random(0)
    board = Board(size=7)
    writer = writer or HintWriter(Role.POLICE, rng, "New York", 15)
    brain = brain_cls(rng=rng, arena="New York", max_words=15, hint_writer=writer)
    engine = GameEngine(
        board=board, role=Role.POLICE, position=(3, 3), barriers=list(barriers or [])
    )
    brain.reset((3, 3))
    return brain, engine, _UniformBelief(board), writer


class TestPhaseOrder:
    """TC-P15 (partial): move phase completes before hint phase."""

    def test_move_before_hint(self) -> None:
        brain, engine, belief, _ = _setup()
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "MOVE:N"
        assert decision.hint != ""
        assert decision.verdict in ("truth", "lie")

    def test_fallback_decide(self) -> None:
        """Forced STAY: legal == ["STAY"] => fallback=True, no barrier consulted."""
        brain, engine, belief, _ = _setup(barriers=_BOXED_IN)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "STAY"
        assert decision.fallback is True
        assert decision.barrier_cell is None


class TestVisitedDiscipline:
    """TC-P18: visited discipline — starts at {start}, grows only on orthogonal MOVE."""

    def test_visited_starts_at_start(self) -> None:
        brain, engine, belief, _ = _setup()
        assert brain.visited == {(3, 3)}
        brain.decide(engine, belief, "", "New York")
        # MOVE:N from (3,3) -> (2,3)
        assert (2, 3) in brain.visited

    def test_stay_does_not_add_to_visited(self) -> None:
        brain, engine, belief, _ = _setup(barriers=_BOXED_IN)
        initial_visited = frozenset(brain.visited)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "STAY"
        assert brain.visited == initial_visited

    def test_reset_clears_visited(self) -> None:
        brain, engine, belief, _ = _setup()
        brain.decide(engine, belief, "", "New York")
        assert len(brain.visited) > 1
        brain.reset((0, 0))
        assert brain.visited == {(0, 0)}


class TestHintFromDestination:
    """The hint is written from the CHOSEN action's destination, never the pre-move
    position (the engine applies the move only after decide() returns).
    """

    def test_movement_hint_gets_post_move_destination(self) -> None:
        brain, engine, belief, spy = _setup(writer=_SpyWriter())
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "MOVE:N"
        assert spy.seen == [(2, 3)]
        assert brain.visited == {(3, 3), (2, 3)}

    def test_stay_hint_gets_current_cell(self) -> None:
        brain, engine, belief, spy = _setup(_StayBrain, writer=_SpyWriter())
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "STAY"
        assert spy.seen == [(3, 3)]
        assert brain.visited == {(3, 3)}

    def test_barrier_turn_hint_gets_current_cell(self) -> None:
        """A barrier forfeits the move, so the peer is still on its own cell."""
        brain, engine, belief, spy = _setup(_BarrierBrain, writer=_SpyWriter())
        decision = brain.decide(engine, belief, "", "New York")
        assert (decision.action, decision.barrier_cell) == ("STAY", (3, 3))
        assert spy.seen == [(3, 3)]
        assert brain.visited == {(3, 3)}

    def test_hint_phase_mutation_cannot_change_the_action(self) -> None:
        """The action is final before the hint phase runs."""
        brain, engine, belief, spy = _setup(writer=_SpyWriter())
        spy.engine = engine
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "MOVE:N"
        assert spy.seen == [(2, 3)]
        assert engine.position == (0, 0)  # the late mutation happened, and changed nothing

    def test_provider_failure_does_not_change_selected_move(self) -> None:
        """A hint provider that raises must never alter the already-selected action."""

        class BoomProvider:
            def generate(self, role, position, arena, max_words, deadline):
                raise RuntimeError("boom")

        writer = HintWriter(Role.POLICE, random.Random(0), "New York", 15, provider=BoomProvider())
        brain, engine, belief, _ = _setup(writer=writer)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "MOVE:N"
        assert decision.hint != ""


class TestNoteEvidence:
    """SD-P5: note_evidence stores the last received field."""

    def test_note_evidence_stores_field(self) -> None:
        brain, _, _, _ = _setup()
        brain.note_evidence({"0,0": 0.9, "1,1": 0.5})
        assert brain.last_field == {"0,0": 0.9, "1,1": 0.5}

    def test_note_evidence_replaces(self) -> None:
        brain, _, _, _ = _setup()
        brain.note_evidence({"0,0": 0.9})
        brain.note_evidence({"2,2": 0.8})
        assert brain.last_field == {"2,2": 0.8}
        assert "0,0" not in brain.last_field
