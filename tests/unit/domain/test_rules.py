"""Tests for GameEngine: movement, barriers, capture, terminal conditions.

Covers BL-06, BL-07, BL-08, BL-09, BL-10, BL-11, BL-12, BL-13, BL-14, BL-15, BL-16, BL-17, BL-18, BL-19.
"""

from __future__ import annotations

import pytest

from police_peer.domain import Board, Cell, GameEngine, IllegalMoveError, Outcome, Role


def make_engine(
    role: Role = Role.POLICE,
    position: Cell = (0, 0),
    size: int = 7,
    barriers_max: int = 14,
    max_steps: int = 35,
    survival_threshold: int = 35,
    barriers: list[Cell] | None = None,
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
    """BL-08: movement, BL-09: diagonal rejection, BL-10: off-board/barrier rejection."""

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


class TestPlaceOwnBarrier:
    """BL-12: placement rules, BL-14: quota, BL-15: declaration."""

    def test_police_can_place_barrier_on_own_cell(self) -> None:
        """BL-12: Police places barrier on own cell."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers_placed=0)
        engine.place_own_barrier((3, 3))
        assert (3, 3) in engine.barriers
        assert engine.barriers_placed == 1

    def test_police_can_place_barrier_on_orthogonal_neighbour(self) -> None:
        """BL-12: Police places barrier on orthogonally adjacent cell."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers_placed=0)
        engine.place_own_barrier((2, 3))
        assert (2, 3) in engine.barriers
        assert engine.barriers_placed == 1

    def test_thief_cannot_place_barrier(self) -> None:
        """BL-12: Thief attempts any placement is rejected."""
        engine = make_engine(role=Role.THIEF, position=(3, 3), barriers_placed=0)
        with pytest.raises(IllegalMoveError, match="only the cop places barriers"):
            engine.place_own_barrier((3, 3))

    def test_barrier_out_of_range_rejected(self) -> None:
        """BL-12: Police at [3,3] targets [3,5] (two steps) is rejected."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers_placed=0)
        with pytest.raises(IllegalMoveError):
            engine.place_own_barrier((3, 5))

    def test_barrier_already_exists_rejected(self) -> None:
        """A barrier already in the set cannot be placed again."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers=[(3, 3)], barriers_placed=1)
        with pytest.raises(IllegalMoveError):
            engine.place_own_barrier((3, 3))

    def test_quota_enforced(self) -> None:
        """BL-14: 15th placement against quota 14 is rejected."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers_max=14, barriers_placed=14)
        with pytest.raises(IllegalMoveError):
            engine.place_own_barrier((2, 3))

    def test_quota_default_is_14(self) -> None:
        """BL-14: default quota is 14."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        assert engine.barriers_max == 14

    def test_barrier_persistence(self) -> None:
        """BL-13: barrier remains after placement."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        engine.place_own_barrier((2, 3))
        assert (2, 3) in engine.barriers
        # No removal API exists — barrier is permanent


class TestObserveBarrier:
    """BL-14: opponent quota, BL-15: declaration."""

    def test_observed_barrier_added(self) -> None:
        """BL-15: declared barrier in bounds, new is appended."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        engine.observe_barrier((2, 3))
        assert (2, 3) in engine.barriers
        assert engine.opponent_barriers == 1

    def test_observed_none_is_noop(self) -> None:
        """None barrier is a no-op."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        engine.observe_barrier(None)
        assert engine.barriers == []
        assert engine.opponent_barriers == 0

    def test_observed_out_of_bounds_rejected(self) -> None:
        """BL-15: declared barrier out of bounds is rejected."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        with pytest.raises(IllegalMoveError, match="off the board"):
            engine.observe_barrier((7, 7))

    def test_opponent_quota_enforced(self) -> None:
        """BL-14: 15th declared opponent barrier against quota 14 is rejected."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers_max=14, opponent_barriers=14)
        with pytest.raises(IllegalMoveError, match="exceeds the signed quota"):
            engine.observe_barrier((2, 3))

    def test_duplicate_observed_barrier_ignored(self) -> None:
        """Duplicate observed barrier does not increment count."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers=[(2, 3)], opponent_barriers=1)
        engine.observe_barrier((2, 3))
        assert engine.opponent_barriers == 1  # not incremented


class TestCaptureByClaim:
    """BL-16: capture by claim."""

    def test_thief_answers_honorable_capture(self) -> None:
        """BL-16: Thief answers truthfully when captured."""
        engine = make_engine(role=Role.THIEF, position=(3, 3))
        result = engine.answer_capture_claim((3, 3))
        assert result == {"claim": [3, 3], "caught": True}

    def test_thief_answers_honorable_miss(self) -> None:
        """BL-16: Thief answers that it is not caught when claim is wrong."""
        engine = make_engine(role=Role.THIEF, position=(3, 3))
        result = engine.answer_capture_claim((2, 2))
        assert result == {"claim": [2, 2], "caught": False}

    def test_police_capture_claim_returns_none(self) -> None:
        """Police does not answer capture claims."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        result = engine.answer_capture_claim((3, 3))
        assert result is None

    def test_none_claim_returns_none(self) -> None:
        """None claim returns None."""
        engine = make_engine(role=Role.THIEF, position=(3, 3))
        result = engine.answer_capture_claim(None)
        assert result is None


class TestSelfCaptured:
    """BL-17: blocking placement, BL-18: entrapment."""

    def test_thief_not_captured_when_free(self) -> None:
        """Thief with legal moves is not self-captured."""
        engine = make_engine(role=Role.THIEF, position=(3, 3))
        assert engine.self_captured() is None

    def test_thief_captured_by_barrier_on_its_cell(self) -> None:
        """BL-17: barrier on Thief's cell is capture."""
        engine = make_engine(role=Role.THIEF, position=(3, 3), barriers=[(3, 3)])
        assert engine.self_captured() == Outcome.CAPTURE

    def test_thief_captured_when_boxed_in(self) -> None:
        """BL-18: Thief with no legal move is captured."""
        engine = make_engine(role=Role.THIEF, position=(1, 1), barriers=[(0, 1), (2, 1), (1, 0), (1, 2)])
        assert engine.self_captured() == Outcome.CAPTURE

    def test_thief_not_captured_with_one_free_cell(self) -> None:
        """BL-18: Thief with one free adjacent cell is not captured."""
        engine = make_engine(role=Role.THIEF, position=(1, 1), barriers=[(0, 1), (2, 1), (1, 0)])
        assert engine.self_captured() is None

    def test_police_self_captured_returns_none(self) -> None:
        """Police never self-captures (it's the pursuer)."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        assert engine.self_captured() is None


class TestSurvived:
    """BL-19: survival threshold."""

    def test_thief_survives_at_threshold(self) -> None:
        """BL-19: Thief survives at threshold of 35 steps."""
        engine = make_engine(role=Role.THIEF, position=(3, 3), step=35)
        assert engine.survived() is True

    def test_thief_not_survived_before_threshold(self) -> None:
        """Thief has not survived before reaching threshold."""
        engine = make_engine(role=Role.THIEF, position=(3, 3), step=34)
        assert engine.survived() is False

    def test_police_never_survives(self) -> None:
        """Police never claims survival."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), step=35)
        assert engine.survived() is False

    def test_custom_survival_threshold(self) -> None:
        """Custom survival threshold is respected."""
        engine = make_engine(role=Role.THIEF, position=(3, 3), survival_threshold=40, step=40)
        assert engine.survived() is True
        engine2 = make_engine(role=Role.THIEF, position=(3, 3), survival_threshold=40, step=39)
        assert engine2.survived() is False


class TestBarrierTargetsMethod:
    """BL-12: barrier targets method."""

    def test_police_barrier_targets(self) -> None:
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        targets = engine.barrier_targets()
        assert (3, 3) in targets
        assert (2, 3) in targets
        assert (4, 3) in targets
        assert (3, 2) in targets
        assert (3, 4) in targets

    def test_thief_barrier_targets_empty(self) -> None:
        engine = make_engine(role=Role.THIEF, position=(3, 3))
        assert engine.barrier_targets() == []

    def test_police_barrier_targets_empty_when_quota_exhausted(self) -> None:
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers_placed=14)
        assert engine.barrier_targets() == []


class TestStateString:
    """Hidden-position design constraint (F-01)."""

    def test_state_string_contains_only_own_position(self) -> None:
        """State string contains only own position, never rival's."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers=[(1, 1)])
        s = engine.state_string()
        assert "self=[3, 3]" in s
        assert "grid=7x7" in s
        assert "[1, 1]" in s  # barrier is public

    def test_state_string_thief(self) -> None:
        engine = make_engine(role=Role.THIEF, position=(5, 5))
        s = engine.state_string()
        assert "self=[5, 5]" in s
