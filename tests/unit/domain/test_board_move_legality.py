"""Tests for Board move legality and entrapment.

Covers BL-08, BL-09, BL-10, BL-11, BL-18.
"""

from __future__ import annotations

from police_peer.domain import ORTHOGONAL, Board


class TestLegalMoves:
    """BL-08: corner move set, BL-09: diagonal rejection,
    BL-10: barrier rejection, BL-11: reproducibility.
    """

    def test_corner_legal_moves(self) -> None:
        """BL-08: from [0,0] legal set is exactly {S, E, STAY}
        in fixed order.
        """
        board = Board(size=7)
        moves = board.legal_moves((0, 0), [])
        assert moves == ["MOVE:S", "MOVE:E", "STAY"]

    def test_center_legal_moves(self) -> None:
        """BL-08: from [3,3] on empty 7x7, legal set is
        {N, S, E, W, STAY} in fixed order.
        """
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
        """BL-11: legal_moves from same (cell, barriers) in two fresh
        instances is identical.
        """
        cell = (3, 3)
        barriers: list[tuple[int, int]] = [(2, 3), (3, 2)]
        board1 = Board(size=7)
        board2 = Board(size=7)
        moves1 = board1.legal_moves(cell, barriers)
        moves2 = board2.legal_moves(cell, barriers)
        assert moves1 == moves2
        assert moves1 is not moves2  # different list objects


class TestBoxedIn:
    """BL-18: entrapment."""

    def test_thief_boxed_in_corner(self) -> None:
        """BL-18: Thief in corner with both adjacent cells barred
        is captured.
        """
        board = Board(size=7)
        # Thief at [0,0], barriers at [0,1] and [1,0]
        barriers = [(0, 1), (1, 0)]
        assert board.boxed_in((0, 0), barriers) is True

    def test_thief_not_boxed_in_corner(self) -> None:
        """BL-18: Thief in corner with one adjacent cell free is
        not captured.
        """
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
        # [0,1] and [1,0] are on edges (not barriers, but out of
        # bounds for movement)
        # Actually, boxed_in only checks if neighbours are in barriers
        barriers = [(0, 1), (2, 1), (1, 0), (1, 2)]
        assert board.boxed_in((1, 1), barriers) is True

    def test_edge_cell_not_boxed_in(self) -> None:
        """Edge cell with one free neighbour is not boxed in."""
        board = Board(size=7)
        barriers = [(0, 2)]  # block east
        # [0,1] has neighbours [0,0] (free), [0,2] (barrier),
        # [1,1] (free)
        assert board.boxed_in((0, 1), barriers) is False
