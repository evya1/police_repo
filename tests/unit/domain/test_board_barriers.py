"""Tests for Board barrier targets and distance utilities.

Covers BL-12.
"""

from __future__ import annotations

from police_peer.domain import Board


class TestBarrierTargets:
    """BL-12: placement rules."""

    def test_barrier_targets_own_cell(self) -> None:
        """Police can place barrier on its own cell."""
        board = Board(size=7)
        targets = board.barrier_targets((3, 3), [])
        assert (3, 3) in targets

    def test_barrier_targets_orthogonal_neighbours(self) -> None:
        """Police can place barrier on orthogonally adjacent cells."""
        board = Board(size=7)
        targets = board.barrier_targets((3, 3), [])
        assert (2, 3) in targets  # N
        assert (4, 3) in targets  # S
        assert (3, 2) in targets  # W
        assert (3, 4) in targets  # E

    def test_barrier_targets_corner(self) -> None:
        """Police at corner has 3 barrier targets: own cell + 2 adjacent."""
        board = Board(size=7)
        targets = board.barrier_targets((0, 0), [])
        assert targets == [(0, 0), (1, 0), (0, 1)]

    def test_barrier_targets_excludes_existing(self) -> None:
        """Barrier targets exclude cells already containing barriers."""
        board = Board(size=7)
        barriers = [(3, 3), (2, 3)]
        targets = board.barrier_targets((3, 3), barriers)
        assert (3, 3) not in targets
        assert (2, 3) not in targets
        assert (4, 3) in targets
        assert (3, 4) in targets
        assert (3, 2) in targets

    def test_barrier_targets_out_of_bounds_excluded(self) -> None:
        """Barrier targets outside board are excluded."""
        board = Board(size=7)
        # At corner [0,0], N and W would be out of bounds
        targets = board.barrier_targets((0, 0), [])
        assert (0, 0) in targets
        assert (1, 0) in targets
        assert (0, 1) in targets
        assert (-1, 0) not in targets
        assert (0, -1) not in targets


class TestManhattanChebyshev:
    """Utility distance functions."""

    def test_manhattan(self) -> None:
        from police_peer.domain import manhattan

        assert manhattan((0, 0), (3, 4)) == 7
        assert manhattan((3, 3), (3, 3)) == 0

    def test_chebyshev(self) -> None:
        from police_peer.domain import chebyshev

        assert chebyshev((0, 0), (3, 4)) == 4
        assert chebyshev((3, 3), (3, 3)) == 0
