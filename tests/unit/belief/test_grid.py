"""BeliefGrid core tests: init, queries, exclude, as_matrix deep copy.

Covers TC-B01, TC-B03, TC-B04, TC-B12(partial), TC-B16.
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief import build_belief
from police_peer.belief.grid import BeliefGrid


def _board(size: int = 7) -> Board:
    return Board(size=size)


def _belief(size: int = 7, **kwargs) -> BeliefGrid:
    cfg = {"belief": kwargs}
    return build_belief(_board(size), cfg, probe=None)


class TestInit:
    """TC-B01: uniform prior over all cells."""

    def test_uniform_7x7(self) -> None:
        bg = _belief()
        for r in range(7):
            for c in range(7):
                assert bg.prob((r, c)) == pytest.approx(1.0 / 49.0)

    def test_sum_is_one(self) -> None:
        bg = _belief()
        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)

    def test_different_size(self) -> None:
        bg = _belief(size=5)
        for r in range(5):
            for c in range(5):
                assert bg.prob((r, c)) == pytest.approx(1.0 / 25.0)


class TestMostLikely:
    """Lexicographic tie-break for most_likely."""

    def test_uniform_tie_break(self) -> None:
        bg = _belief()
        assert bg.most_likely() == (0, 0)

    def test_peak_after_observation(self) -> None:
        bg = _belief()
        bg.observe_smell({"3,3": 0.9})
        assert bg.most_likely() == (3, 3)

    def test_peak_probability(self) -> None:
        bg = _belief()
        bg.observe_smell({"3,3": 0.9})
        peak = bg.peak_probability()
        assert peak == pytest.approx(bg.prob((3, 3)))


class TestTopK:
    """top_k returns cells sorted by probability descending, then lexicographic."""

    def test_top_k_order(self) -> None:
        bg = _belief()
        bg.observe_smell({"3,3": 0.9})
        top = bg.top_k(3)
        assert top[0][0] == (3, 3)
        assert top[0][1] == pytest.approx(4.6 / 52.6, abs=1e-4)

    def test_top_k_exceeds_board(self) -> None:
        bg = _belief(size=3)
        top = bg.top_k(100)
        assert len(top) == 9


class TestExclude:
    """TC-B03: exclude zeroes a cell and renormalizes."""

    def test_exclude_barrier_cell(self) -> None:
        bg = _belief()
        bg.exclude((3, 3))
        assert bg.prob((3, 3)) == pytest.approx(0.0)
        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)

    def test_exclude_out_of_bounds(self) -> None:
        bg = _belief()
        bg.exclude((10, 10))
        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)

    def test_exclude_multiple(self) -> None:
        bg = _belief()
        bg.exclude((0, 0))
        bg.exclude((6, 6))
        assert bg.prob((0, 0)) == pytest.approx(0.0)
        assert bg.prob((6, 6)) == pytest.approx(0.0)
        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)


class TestSelfExclusion:
    """TC-B04: self-exclusion gated on capture_landed."""

    def test_exclude_own_cell_no_capture(self) -> None:
        from police_peer.belief.update import apply_half_turn

        bg = _belief()
        apply_half_turn(
            bg,
            barrier=None,
            field={},
            hint="",
            arena="New York",
            own_cell=(3, 3),
            capture_landed=False,
        )
        assert bg.prob((3, 3)) == pytest.approx(0.0)

    def test_keep_own_cell_with_capture(self) -> None:
        from police_peer.belief.update import apply_half_turn

        bg = _belief()
        apply_half_turn(
            bg,
            barrier=None,
            field={},
            hint="",
            arena="New York",
            own_cell=(3, 3),
            capture_landed=True,
        )
        assert bg.prob((3, 3)) > 0.0


class TestAsMatrix:
    """TC-B16: as_matrix is a deep copy."""

    def test_deep_copy(self) -> None:
        bg = _belief()
        mat = bg.as_matrix()
        mat[0][0] = 999.0
        assert bg.prob((0, 0)) == pytest.approx(1.0 / 49.0)

    def test_matrix_matches_prob(self) -> None:
        bg = _belief()
        mat = bg.as_matrix()
        for r in range(7):
            for c in range(7):
                assert mat[r][c] == pytest.approx(bg.prob((r, c)))
