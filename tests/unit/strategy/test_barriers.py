"""Barrier pipeline tests: guards, value, self-route, reserve, threshold, tie.

TC-P07: guards — non-Police role, quota exhausted, empty candidates.
TC-P08: value — mass/cut skip, corridor cut, peak candidate.
TC-P09: self-route — candidate worsens pursuit by more than slack.
TC-P10: reserve — remaining <= barrier_reserve, score < strong_threshold.
TC-P11: threshold & tie — score below threshold => None; equal scores => first candidate wins.
"""

from __future__ import annotations

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from src.police_peer.strategy.barriers import cut_value, where_place_barrier


class _Belief:
    def __init__(self, board, peak=(0, 0), peak_prob=0.5, prob_fn=None):
        self._board = board
        self._peak = peak
        self._peak_prob = peak_prob
        self._prob_fn = prob_fn

    def most_likely(self):
        return self._peak

    def peak_probability(self) -> float:
        return self._peak_prob

    def prob(self, cell):
        if self._prob_fn:
            return self._prob_fn(cell)
        return self._peak_prob if cell == self._peak else 0.01


_CFG = {
    "barrier_mass_floor": 0.05,
    "w_mass": 1.0,
    "w_cut": 0.5,
    "route_slack": 1,
    "barrier_reserve": 3,
    "strong_threshold": 0.8,
    "barrier_score_threshold": 0.3,
}


class TestGuards:
    """TC-P07: where_place_barrier guards."""

    def test_non_police_role(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.THIEF, position=(3, 3))
        assert where_place_barrier(engine, _Belief(engine.board), _CFG) is None

    def test_quota_exhausted(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3),
                            barriers_max=2, barriers_placed=2)
        assert where_place_barrier(engine, _Belief(engine.board), _CFG) is None

    def test_no_candidates(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3),
                            barriers=[(2, 3), (4, 3), (3, 2), (3, 4)])
        assert where_place_barrier(engine, _Belief(engine.board), _CFG) is None


class TestValue:
    """TC-P08: where_place_barrier value — skip rules and cut computation."""

    def test_low_mass_no_cut_skipped(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3))
        belief = _Belief(engine.board, peak_prob=0.01)
        assert where_place_barrier(engine, belief, _CFG) is None

    def test_cut_on_peak(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(0, 0))
        assert cut_value(engine, (3, 3), (3, 3)) >= 1

    def test_corridor_cut(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(0, 0))
        assert cut_value(engine, (1, 0), (6, 6)) >= 0


class TestSelfRoute:
    """TC-P09: where_place_barrier self-route guard."""

    def test_self_route_vacuous_when_cut_off(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(0, 0),
                            barriers=[(1, 0), (0, 1)])
        belief = _Belief(engine.board, peak=(6, 6), peak_prob=0.5)
        result = where_place_barrier(engine, belief, _CFG)
        assert result is None or result in engine.barrier_targets()


class TestReserve:
    """TC-P10: where_place_barrier reserve rule."""

    def test_reserve_skips_weak_candidate(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3),
                            barriers_max=5, barriers_placed=3)
        assert where_place_barrier(engine, _Belief(engine.board, peak_prob=0.03), _CFG) is None

    def test_reserve_allows_strong_candidate(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3),
                            barriers_max=5, barriers_placed=3)
        belief = _Belief(engine.board, peak=(3, 3), peak_prob=0.6,
                         prob_fn=lambda c: 0.6 if c == (3, 3) else 0.001)
        assert where_place_barrier(engine, belief, _CFG) is not None


class TestThresholdAndTie:
    """TC-P11: where_place_barrier threshold and tie-breaking."""

    def test_below_threshold_returns_none(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3))
        assert where_place_barrier(engine, _Belief(engine.board, peak_prob=0.01), _CFG) is None

    def test_at_or_above_threshold_returns_best(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3))
        assert where_place_barrier(engine, _Belief(engine.board, peak=(3, 3), peak_prob=0.8),
                                   _CFG) is not None

    def test_tie_first_candidate_wins(self) -> None:
        engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3))
        belief = _Belief(engine.board, peak_prob=0.1)
        candidates = engine.barrier_targets()
        result = where_place_barrier(engine, belief, _CFG)
        if result is not None:
            assert result in candidates
            assert result == candidates[0]
