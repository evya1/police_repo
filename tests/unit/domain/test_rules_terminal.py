"""Tests for GameEngine terminal conditions and state.

Covers BL-19, F-01.
"""

from __future__ import annotations

from police_peer.domain import Board, GameEngine, Role


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
        engine = make_engine(
            role=Role.THIEF,
            position=(3, 3),
            survival_threshold=40,
            step=40,
        )
        assert engine.survived() is True
        engine2 = make_engine(
            role=Role.THIEF,
            position=(3, 3),
            survival_threshold=40,
            step=39,
        )
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

    def test_police_barrier_targets_empty_when_quota_exhausted(
        self,
    ) -> None:
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
