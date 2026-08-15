"""Tests for GameEngine movement and legal move enumeration.

Covers BL-08, BL-09, BL-11.
"""

from __future__ import annotations

import pytest

from police_peer.domain import Board, GameEngine, IllegalMoveError, Role


def make_engine(
    role: Role = Role.POLICE,
    position: tuple[int, int] = (0, 0),
    size: int = 7,
    barriers_max: int = 14,
    max_steps: int = 35,
    survival_threshold: int = 35,
    barriers: list[tuple[int, int]] | None = None,
    barriers_placed: int = 0,
    step: int = 0,
    opponent_barriers: int = 0,
) -> GameEngine:
    board = Board(size=size)
    return GameEngine(
        board=board,
        role=role,
        position=position,
        barriers_max=barriers_max,
        max_steps=max_steps,
        survival_threshold=survival_threshold,
        barriers=barriers or [],
        barriers_placed=barriers_placed,
        step=step,
        opponent_barriers=opponent_barriers,
    )


class TestLegalMoves:
    """BL-08: legal move enumeration, BL-11: reproducibility."""

    def test_police_legal_moves_corner(self) -> None:
        """BL-08: Police at [0,0] has legal moves S, E, STAY."""
        engine = make_engine(role=Role.POLICE, position=(0, 0))
        moves = engine.legal_moves()
        assert moves == ["MOVE:S", "MOVE:E", "STAY"]

    def test_thief_legal_moves_center(self) -> None:
        """BL-08: Thief at [3,3] on empty 7x7 has all 5 moves."""
        engine = make_engine(role=Role.THIEF, position=(3, 3))
        moves = engine.legal_moves()
        assert moves == ["MOVE:N", "MOVE:S", "MOVE:W", "MOVE:E", "STAY"]

    def test_no_diagonal(self) -> None:
        """BL-09: no diagonal moves are legal."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        moves = engine.legal_moves()
        for m in moves:
            assert m in ["MOVE:N", "MOVE:S", "MOVE:W", "MOVE:E", "STAY"]


class TestApplyOwnMove:
    """BL-08: movement, BL-09: diagonal rejection,
    BL-10: off-board/barrier rejection.
    """

    def test_move_north(self) -> None:
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        engine.apply_own_move("MOVE:N")
        assert engine.position == (2, 3)
        assert engine.step == 1

    def test_move_south(self) -> None:
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        engine.apply_own_move("MOVE:S")
        assert engine.position == (4, 3)

    def test_move_east(self) -> None:
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        engine.apply_own_move("MOVE:E")
        assert engine.position == (3, 4)

    def test_move_west(self) -> None:
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        engine.apply_own_move("MOVE:W")
        assert engine.position == (3, 2)

    def test_move_stay(self) -> None:
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        engine.apply_own_move("STAY")
        assert engine.position == (3, 3)
        assert engine.step == 1

    def test_off_board_move_rejected(self) -> None:
        """BL-10: N from [0,0] is rejected."""
        engine = make_engine(role=Role.POLICE, position=(0, 0))
        with pytest.raises(IllegalMoveError):
            engine.apply_own_move("MOVE:N")

    def test_barrier_move_rejected(self) -> None:
        """BL-10: move into a barrier cell is rejected."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers=[(3, 4)])
        with pytest.raises(IllegalMoveError):
            engine.apply_own_move("MOVE:E")

    def test_step_counter_increments(self) -> None:
        engine = make_engine(role=Role.POLICE, position=(3, 3), step=5)
        engine.apply_own_move("MOVE:N")
        assert engine.step == 6

    def test_reproducibility(self) -> None:
        """BL-11: same initial state produces identical move sequences."""
        e1 = make_engine(role=Role.POLICE, position=(3, 3))
        e2 = make_engine(role=Role.POLICE, position=(3, 3))
        for move in ["MOVE:N", "MOVE:E", "STAY"]:
            e1.apply_own_move(move)
            e2.apply_own_move(move)
        assert e1.position == e2.position
        assert e1.step == e2.step
        assert e1.barriers == e2.barriers
