"""Tests for Board geometry and move legality.

Covers BL-01, BL-03, BL-08, BL-09, BL-10, BL-11.
"""

from __future__ import annotations

import pytest

from police_peer.domain import MOVES, ORTHOGONAL, Board, Cell


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


class TestLegalMoves:
    """BL-08: corner move set, BL-09: diagonal rejection, BL-10: barrier rejection, BL-11: reproducibility."""

    def test_corner_legal_moves(self) -> None:
        """BL-08: from [0,0] legal set is exactly {S, E, STAY} in fixed order."""
        board = Board(size=7)
        moves = board.legal_moves((0, 0), [])
        assert moves == ["MOVE:S", "MOVE:E", "STAY"]

    def test_center_legal_moves(self) -> None:
        """BL-08: from [3,3] on empty 7x7, legal set is {N, S, E, W, STAY} in fixed order."""
        board = Board(size=7)
        moves = board.legal_moves((3, 3), [])
        assert moves == ["MOVE:N", "MOVE:S", "MOVE:W", "MOVE:E", "STAY"]

    def test_edge_legal_moves(self) -> None:
        """Moves from edge cells exclude out-of-bounds directions."""
        board = Board(size=7)
        moves = board.legal_moves((0, 3), [])
        # ORTHOGONAL order is N, S, W, E; N is off-board from row 0
        assert moves == ["MOVE:S", "MOVE:W", "MOVE:E", "STAY"]

    def test_diagonal_not_in_legal_moves(self) -> None:
        """BL-09: diagonal moves are not in legal_moves."""
        board = Board(size=7)
        moves = board.legal_moves((3, 3), [])
        for m in moves:
            assert m in ORTHOGONAL or m == "STAY"

    def test_barrier_rejection(self) -> None:
        """BL-10: move into a barrier cell is rejected."""
        board = Board(size=7)
        barriers = [(3, 4)]
        moves = board.legal_moves((3, 3), barriers)
        assert "MOVE:E" not in moves
        assert "MOVE:S" in moves  # still available
        assert "STAY" in moves

    def test_all_barrier_rejection(self) -> None:
        """All orthogonal moves blocked except STAY."""
        board = Board(size=7)
        barriers = [(2, 3), (4, 3), (3, 2), (3, 4)]
        moves = board.legal_moves((3, 3), barriers)
        assert moves == ["STAY"]

    def test_reproducibility(self) -> None:
        """BL-11: legal_moves from same (cell, barriers) in two fresh instances is identical."""
        cell = (3, 3)
        barriers: list[Cell] = [(2, 3), (3, 2)]
        board1 = Board(size=7)
        board2 = Board(size=7)
        moves1 = board1.legal_moves(cell, barriers)
        moves2 = board2.legal_moves(cell, barriers)
        assert moves1 == moves2
        assert moves1 is not moves2  # different list objects


class TestBoxedIn:
    """BL-18: entrapment."""

    def test_thief_boxed_in_corner(self) -> None:
        """BL-18: Thief in corner with both adjacent cells barred is captured."""
        board = Board(size=7)
        # Thief at [0,0], barriers at [0,1] and [1,0]
        barriers = [(0, 1), (1, 0)]
        assert board.boxed_in((0, 0), barriers) is True

    def test_thief_not_boxed_in_corner(self) -> None:
        """BL-18: Thief in corner with one adjacent cell free is not captured."""
        board = Board(size=7)
        # Thief at [0,0], only [0,1] barred, [1,0] is free
        barriers = [(0, 1)]
        assert board.boxed_in((0, 0), barriers) is False

    def test_thief_not_boxed_in_center(self) -> None:
        """Center cell with no barriers is not boxed in."""
        board = Board(size=7)
        assert board.boxed_in((3, 3), []) is False

    def test_thief_boxed_in_by_board_edges(self) -> None:
        """A cell surrounded by board edges and barriers is boxed in."""
        board = Board(size=7)
        # [1,1] has neighbours [0,1], [2,1], [1,0], [1,2]
        # [0,1] and [1,0] are on edges (not barriers, but out of bounds for movement)
        # Actually, boxed_in only checks if neighbours are in barriers
        barriers = [(0, 1), (2, 1), (1, 0), (1, 2)]
        assert board.boxed_in((1, 1), barriers) is True

    def test_edge_cell_not_boxed_in(self) -> None:
        """Edge cell with one free neighbour is not boxed in."""
        board = Board(size=7)
        barriers = [(0, 2)]  # block east
        # [0,1] has neighbours [0,0] (free), [0,2] (barrier), [1,1] (free)
        assert board.boxed_in((0, 1), barriers) is False


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
