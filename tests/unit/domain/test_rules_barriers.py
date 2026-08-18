"""Tests for GameEngine barrier placement and observation.

Covers BL-12, BL-13, BL-14, BL-15.
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


class TestPlaceOwnBarrier:
    """BL-12: placement rules, BL-14: quota, BL-15: declaration."""

    def test_police_can_place_barrier_on_own_cell(self) -> None:
        """BL-12: Police places barrier on own cell."""
        engine = make_engine(role=Role.POLICE, position=(3, 3), barriers_placed=0)
        engine.place_own_barrier((3, 3))
        assert (3, 3) in engine.barriers
        assert engine.barriers_placed == 1

    def test_police_can_place_barrier_on_orthogonal_neighbour(
        self,
    ) -> None:
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
        engine = make_engine(
            role=Role.POLICE,
            position=(3, 3),
            barriers=[(3, 3)],
            barriers_placed=1,
        )
        with pytest.raises(IllegalMoveError):
            engine.place_own_barrier((3, 3))

    def test_quota_enforced(self) -> None:
        """BL-14: 15th placement against quota 14 is rejected."""
        engine = make_engine(
            role=Role.POLICE,
            position=(3, 3),
            barriers_max=14,
            barriers_placed=14,
        )
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
        """BL-14: 15th declared opponent barrier against quota 14
        is rejected.
        """
        engine = make_engine(
            role=Role.POLICE,
            position=(3, 3),
            barriers_max=14,
            opponent_barriers=14,
        )
        with pytest.raises(IllegalMoveError, match="exceeds the signed quota"):
            engine.observe_barrier((2, 3))

    def test_duplicate_observed_barrier_ignored(self) -> None:
        """Duplicate observed barrier does not increment count."""
        engine = make_engine(
            role=Role.POLICE,
            position=(3, 3),
            barriers=[(2, 3)],
            opponent_barriers=1,
        )
        engine.observe_barrier((2, 3))
        assert engine.opponent_barriers == 1  # not incremented
