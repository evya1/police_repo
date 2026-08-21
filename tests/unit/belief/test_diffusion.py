"""Diffusion tests: neighbourhood spreading.

Covers TC-B09.
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief.grid import BeliefGrid


def _point_mass_board(size: int = 7, center: tuple[int, int] = (3, 3)) -> BeliefGrid:
    """Create a BeliefGrid with all mass on a single cell."""
    board = Board(size=size)
    bg = BeliefGrid(board)
    for r in range(size):
        for c in range(size):
            if (r, c) != center:
                bg._matrix[r][c] = 0.0
    bg._normalize()
    return bg


class TestDiffusion:
    """TC-B09: diffusion from a point mass spreads to self + 4 ortho neighbours."""

    def test_center_spreads_to_five(self) -> None:
        bg = _point_mass_board(7, (3, 3))
        bg.diffuse()
        assert bg.prob((3, 3)) == pytest.approx(1.0 / 5.0)
        assert bg.prob((2, 3)) == pytest.approx(1.0 / 5.0)
        assert bg.prob((4, 3)) == pytest.approx(1.0 / 5.0)
        assert bg.prob((3, 2)) == pytest.approx(1.0 / 5.0)
        assert bg.prob((3, 4)) == pytest.approx(1.0 / 5.0)
        assert bg.prob((2, 2)) == pytest.approx(0.0)
        assert bg.prob((2, 4)) == pytest.approx(0.0)
        assert bg.prob((4, 2)) == pytest.approx(0.0)
        assert bg.prob((4, 4)) == pytest.approx(0.0)
        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)

    def test_corner_spreads_to_three(self) -> None:
        bg = _point_mass_board(7, (0, 0))
        bg.diffuse()
        assert bg.prob((0, 0)) == pytest.approx(1.0 / 3.0)
        assert bg.prob((1, 0)) == pytest.approx(1.0 / 3.0)
        assert bg.prob((0, 1)) == pytest.approx(1.0 / 3.0)
        assert bg.prob((0, 2)) == pytest.approx(0.0)
        assert bg.prob((2, 0)) == pytest.approx(0.0)
        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)

    def test_no_diagonals(self) -> None:
        """Diffusion never spreads to diagonal cells."""
        bg = _point_mass_board(7, (3, 3))
        bg.diffuse()
        for dr in (-1, 1):
            for dc in (-1, 1):
                assert bg.prob((3 + dr, 3 + dc)) == pytest.approx(0.0)

    def test_sum_preserved(self) -> None:
        """Diffusion preserves total probability mass."""
        bg = BeliefGrid(Board(size=7))
        bg._matrix[0][0] = 0.5
        bg._matrix[0][1] = 0.5
        bg._normalize()
        before = sum(sum(row) for row in bg._matrix)
        bg.diffuse()
        after = sum(sum(row) for row in bg._matrix)
        assert after == pytest.approx(before)


class TestDiffusePure:
    """Test the pure diffuse function from update.py."""

    def test_pure_diffuse(self) -> None:
        from police_peer.belief.update import diffuse

        probs = [[0.0] * 7 for _ in range(7)]
        probs[3][3] = 1.0
        result = diffuse(probs, 7)
        assert result[3][3] == pytest.approx(1.0 / 5.0)
        assert result[2][3] == pytest.approx(1.0 / 5.0)
        assert result[4][3] == pytest.approx(1.0 / 5.0)
        assert result[3][2] == pytest.approx(1.0 / 5.0)
        assert result[3][4] == pytest.approx(1.0 / 5.0)
