"""Tests for GameEngine capture and entrapment.

Covers BL-16, BL-17, BL-18.
"""

from __future__ import annotations

from police_peer.domain import Board, GameEngine, Outcome, Role


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


class TestCaptureByClaim:
    """BL-16: capture by claim."""

    def test_thief_answers_honorable_capture(self) -> None:
        """BL-16: Thief answers truthfully when captured."""
        engine = make_engine(role=Role.THIEF, position=(3, 3))
        result = engine.answer_capture_claim((3, 3))
        assert result == {"claim": [3, 3], "caught": True}

    def test_thief_answers_honorable_miss(self) -> None:
        """BL-16: Thief answers that it is not caught when claim
        is wrong.
        """
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
        engine = make_engine(
            role=Role.THIEF,
            position=(1, 1),
            barriers=[(0, 1), (2, 1), (1, 0), (1, 2)],
        )
        assert engine.self_captured() == Outcome.CAPTURE

    def test_thief_not_captured_with_one_free_cell(self) -> None:
        """BL-18: Thief with one free adjacent cell is not captured."""
        engine = make_engine(
            role=Role.THIEF,
            position=(1, 1),
            barriers=[(0, 1), (2, 1), (1, 0)],
        )
        assert engine.self_captured() is None

    def test_police_self_captured_returns_none(self) -> None:
        """Police never self-captures (it's the pursuer)."""
        engine = make_engine(role=Role.POLICE, position=(3, 3))
        assert engine.self_captured() is None
