"""TC-P02 full: property tests for strategy policy over 10k random seeded fixtures.

Verifies:
- action is always in the legal set;
- barrier_cell is None or a legal candidate with action == "STAY" and quota respected;
- fallback flag is exact (True iff legal == ["STAY"]).
"""

from __future__ import annotations

import random

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from police_peer.strategy.police import PoliceBrain


class _UniformBelief:
    """Uniform belief: peak probability = 1/N²."""

    def __init__(self, board):
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


def _random_barrier_targets(board, position, num_barriers, rng):
    """Generate a list of random barrier cells near the position."""
    barriers = []
    # Add some random barriers elsewhere on the board
    for _ in range(num_barriers):
        r = rng.randint(0, board.size - 1)
        c = rng.randint(0, board.size - 1)
        cell = (r, c)
        if board.in_bounds(cell) and cell not in barriers and cell != position:
            barriers.append(cell)
    return barriers


def _make_engine(rng, board_size, position, barriers=None, barriers_max=14, barriers_placed=0):
    """Create a GameEngine with random or fixed parameters."""
    board = Board(size=board_size)
    if barriers is None:
        barriers = []
    return GameEngine(
        board=board,
        role=Role.POLICE,
        position=position,
        barriers=barriers,
        barriers_placed=barriers_placed,
        barriers_max=barriers_max,
    )


def _make_belief(rng, board, use_peak=True, peak=None):
    """Create a belief object."""
    if use_peak and peak is not None:
        return _PeakBelief(board, peak, peak_prob=rng.random() * 0.8 + 0.1)
    return _UniformBelief(board)


def test_tc_p02_action_in_legal_set() -> None:
    """TC-P02a: action is always in the legal set over 10k random fixtures."""
    rng = random.Random(42)
    brain = PoliceBrain()
    failures = 0
    for i in range(10_000):
        board_size = rng.randint(5, 11)
        position = (rng.randint(0, board_size - 1), rng.randint(0, board_size - 1))
        num_barriers = rng.randint(0, 8)
        barriers = _random_barrier_targets(Board(size=board_size), position, num_barriers, rng)
        engine = _make_engine(rng, board_size, position, barriers)
        belief = _make_belief(rng, engine.board, use_peak=rng.random() > 0.3)
        action, _ = brain._decide_move(engine, belief)
        if action not in engine.legal_moves():
            failures += 1
            if failures <= 5:
                print(f"FAIL i={i}: action={action!r} not in {engine.legal_moves()}")
    assert failures == 0, f"action not in legal set in {failures}/10000 fixtures"


def test_tc_p02_barrier_cell_constraints() -> None:
    """TC-P02b: barrier_cell is None or legal candidate with action==STAY and quota respected."""
    rng = random.Random(43)
    brain = PoliceBrain()
    failures = 0
    for i in range(10_000):
        board_size = rng.randint(5, 11)
        position = (rng.randint(0, board_size - 1), rng.randint(0, board_size - 1))
        num_barriers = rng.randint(0, 8)
        barriers = _random_barrier_targets(Board(size=board_size), position, num_barriers, rng)
        barriers_max = rng.randint(5, 14)
        barriers_placed = rng.randint(0, min(num_barriers, barriers_max))
        engine = _make_engine(rng, board_size, position, barriers, barriers_max, barriers_placed)
        belief = _make_belief(rng, engine.board, use_peak=rng.random() > 0.3)
        action, barrier = brain._decide_move(engine, belief)
        if barrier is not None:
            if action != "STAY":
                failures += 1
                if failures <= 5:
                    print(f"FAIL i={i}: barrier set but action={action!r} != STAY")
            if barrier not in engine.barrier_targets():
                failures += 1
                if failures <= 5:
                    print(f"FAIL i={i}: barrier {barrier} not in barrier_targets()")
            if engine.barriers_placed >= engine.barriers_max:
                failures += 1
                if failures <= 5:
                    print(f"FAIL i={i}: barrier set but quota exhausted (placed={engine.barriers_placed}, max={engine.barriers_max})")
    assert failures == 0, f"barrier constraints violated in {failures}/10000 fixtures"


def test_tc_p02_fallback_exact() -> None:
    """TC-P02c: fallback flag is exact (True iff legal == ["STAY"])."""
    rng = random.Random(44)
    brain = PoliceBrain()
    failures = 0
    for i in range(10_000):
        board_size = rng.randint(5, 11)
        position = (rng.randint(0, board_size - 1), rng.randint(0, board_size - 1))
        num_barriers = rng.randint(0, 8)
        barriers = _random_barrier_targets(Board(size=board_size), position, num_barriers, rng)
        engine = _make_engine(rng, board_size, position, barriers)
        belief = _make_belief(rng, engine.board, use_peak=rng.random() > 0.3)
        legal = engine.legal_moves()
        expected_fallback = legal == ["STAY"]
        decision = brain.decide(engine, belief, "", "New York")
        if decision.fallback != expected_fallback:
            failures += 1
            if failures <= 5:
                print(f"FAIL i={i}: fallback={decision.fallback} but legal={legal}, expected={expected_fallback}")
    assert failures == 0, f"fallback flag inexact in {failures}/10000 fixtures"


def test_tc_p02_deterministic_same_seed() -> None:
    """TC-P02d: same seed + same fixture => identical decisions."""
    rng_seed = 12345
    board_size = 7
    position = (3, 3)
    barriers = [(2, 3), (3, 2)]
    peak = (5, 5)

    def run_once(seed):
        rng = random.Random(seed)
        brain = PoliceBrain()
        engine = _make_engine(rng, board_size, position, barriers)
        belief = _PeakBelief(engine.board, peak, peak_prob=0.5)
        return brain._decide_move(engine, belief)

    result1 = run_once(rng_seed)
    result2 = run_once(rng_seed)
    assert result1 == result2, f"non-deterministic: {result1} != {result2}"
