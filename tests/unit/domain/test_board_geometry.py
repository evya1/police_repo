"""Tests for Board geometry and move mapping.

Covers BL-01, BL-03, BL-08, BL-09.
"""

from __future__ import annotations

import pytest

from police_peer.domain import MOVES, ORTHOGONAL, Board


class TestBoardGeometry:
    """BL-01: board geometry, BL-03: defaults."""

    def test_default_size(self) -> None:
        """Default board is 7x7."""
        board = Board(size=7)
        assert board.size == 7

    def test_in_bounds_7x7(self) -> None:
        """BL-01: cells [3,3], [0,0], [6,6] in bounds on 7x7."""
        board = Board(size=7)
        assert board.in_bounds((3, 3)) is True
        assert board.in_bounds((0, 0)) is True
        assert board.in_bounds((6, 6)) is True

    def test_out_of_bounds_7x7(self) -> None:
        """BL-01: [7,0], [-1,3] out of bounds on 7x7."""
        board = Board(size=7)
        assert board.in_bounds((7, 0)) is False
        assert board.in_bounds((-1, 3)) is False
        assert board.in_bounds((3, 7)) is False
        assert board.in_bounds((3, -1)) is False

    def test_smallest_valid_board(self) -> None:
        """BL-01: board must be at least 7x7 — 7 is the binding minimum."""
        board = Board(size=7)
        assert board.in_bounds((0, 0)) is True
        assert board.in_bounds((6, 6)) is True
        assert board.in_bounds((7, 7)) is False

    def test_larger_board(self) -> None:
        """BL-01: board can be larger than 7x7."""
        board = Board(size=9)
        assert board.in_bounds((4, 4)) is True
        assert board.in_bounds((8, 8)) is True
        assert board.in_bounds((9, 9)) is False

    def test_center_cell_default(self) -> None:
        """BL-03: Thief start [3,3] is center of 7x7."""
        board = Board(size=7)
        assert board.in_bounds((3, 3)) is True
        # Verify it's equidistant from all edges
        assert board.in_bounds((3, 3)) is True

    def test_corner_cell_default(self) -> None:
        """BL-03: Police start [0,0] is a corner of 7x7."""
        board = Board(size=7)
        assert board.in_bounds((0, 0)) is True

    def test_board_is_frozen(self) -> None:
        """Board is immutable."""
        board = Board(size=7)
        with pytest.raises(AttributeError):
            board.size = 8  # type: ignore[misc]


class TestMoveMapping:
    """BL-08: corner move set, BL-09: diagonal rejection."""

    def test_move_mappings(self) -> None:
        """All move mappings are correct."""
        assert MOVES["MOVE:N"] == (-1, 0)
        assert MOVES["MOVE:S"] == (1, 0)
        assert MOVES["MOVE:E"] == (0, 1)
        assert MOVES["MOVE:W"] == (0, -1)
        assert MOVES["STAY"] == (0, 0)

    def test_orthogonal_constant(self) -> None:
        """ORTHOGONAL contains exactly the four cardinal moves."""
        assert ORTHOGONAL == ("MOVE:N", "MOVE:S", "MOVE:W", "MOVE:E")

    def test_no_diagonal_moves(self) -> None:
        """BL-09: no diagonal moves in the move set."""
        for move in MOVES:
            dr, dc = MOVES[move]
            # Diagonal would have both dr and dc non-zero
            assert not (dr != 0 and dc != 0), f"{move} is diagonal"


class TestStep:
    """BL-08: corner move set, BL-10: off-board rejection."""

    def test_step_north(self) -> None:
        board = Board(size=7)
        assert board.step((3, 3), "MOVE:N") == (2, 3)

    def test_step_south(self) -> None:
        board = Board(size=7)
        assert board.step((3, 3), "MOVE:S") == (4, 3)

    def test_step_east(self) -> None:
        board = Board(size=7)
        assert board.step((3, 3), "MOVE:E") == (3, 4)

    def test_step_west(self) -> None:
        board = Board(size=7)
        assert board.step((3, 3), "MOVE:W") == (3, 2)

    def test_step_stay(self) -> None:
        board = Board(size=7)
        assert board.step((3, 3), "STAY") == (3, 3)

    def test_off_board_north_from_corner(self) -> None:
        """BL-10: N from [0,0] goes off board."""
        board = Board(size=7)
        result = board.step((0, 0), "MOVE:N")
        assert result == (-1, 0)  # step computes; in_bounds rejects

    def test_step_to_corner(self) -> None:
        board = Board(size=7)
        assert board.step((1, 1), "MOVE:N") == (0, 1)
        assert board.step((1, 1), "MOVE:W") == (1, 0)
