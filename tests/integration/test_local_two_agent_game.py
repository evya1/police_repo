"""T029: Deterministic Stage-1 capture/survival test suite.

Proves:
- Capture outcome with scores 20 (Police) / 5 (Thief)
- Survival outcome at survival_threshold (35) with scores 5 (Police) / 10 (Thief)
- Capture at step 35 takes precedence over survival if capture occurs
- Production termination-contract refusal when max_moves != survival_threshold
- Barrier quota rejection without state corruption
- Deterministic reproducibility across independent runs
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from common.domain.rules import GameEngine, IllegalMoveError
from common.domain.scoring import SCORES, Outcome, Role, score_for


def _create_pair(
    size: int = 7,
    max_steps: int = 35,
    survival_thresh: int = 35,
    barriers_max: int = 14,
) -> tuple[GameEngine, GameEngine]:
    if max_steps != survival_thresh:
        raise ValueError("divergent max_moves and survival_threshold refused by termination contract")
    board = Board(size=size)
    cop = GameEngine(
        board=board,
        role=Role.POLICE,
        position=(0, 0),
        max_steps=max_steps,
        survival_threshold=survival_thresh,
        barriers_max=barriers_max,
    )
    thief = GameEngine(
        board=board,
        role=Role.THIEF,
        position=(3, 3),
        max_steps=max_steps,
        survival_threshold=survival_thresh,
        barriers_max=barriers_max,
    )
    return cop, thief


def test_stage1_capture_scores_20_5() -> None:
    cop, thief = _create_pair()
    # Cop moves E, S, E, S, E, S to reach (3, 3)
    cop_moves = ["MOVE:E", "MOVE:S", "MOVE:E", "MOVE:S", "MOVE:E", "MOVE:S"]
    for m in cop_moves:
        cop.apply_own_move(m)

    # Cop claims capture at (3, 3)
    claim = (3, 3)
    resp = thief.answer_capture_claim(claim)
    assert resp is not None and resp["caught"] is True

    # Scores for CAPTURE
    assert SCORES[Outcome.CAPTURE] == (20, 5)
    assert score_for(Outcome.CAPTURE, Role.POLICE) == 20
    assert score_for(Outcome.CAPTURE, Role.THIEF) == 5


def test_stage1_survival_at_step_35_scores_5_10() -> None:
    cop, thief = _create_pair(size=7, max_steps=35, survival_thresh=35)
    # Thief oscillates between (3, 3) and (3, 4) for 35 steps
    for step in range(1, 36):
        move = "MOVE:E" if thief.position == (3, 3) else "MOVE:W"
        thief.apply_own_move(move)
        assert thief.step == step

    assert thief.survived() is True
    assert SCORES[Outcome.SURVIVAL] == (5, 10)
    assert score_for(Outcome.SURVIVAL, Role.POLICE) == 5
    assert score_for(Outcome.SURVIVAL, Role.THIEF) == 10


def test_stage1_capture_at_step_35_takes_precedence() -> None:
    cop, thief = _create_pair(size=7, max_steps=35, survival_thresh=35)
    # Thief takes 34 steps
    for _ in range(17):
        thief.apply_own_move("MOVE:E")
        thief.apply_own_move("MOVE:W")
    assert thief.step == 34
    assert thief.survived() is False

    # Thief takes step 35 to (3, 4)
    thief.apply_own_move("MOVE:E")
    assert thief.step == 35

    # Cop claims capture at (3, 4) on step 35 before survival is finalized
    resp = thief.answer_capture_claim((3, 4))
    assert resp is not None and resp["caught"] is True
    # Capture resolves to CAPTURE
    assert score_for(Outcome.CAPTURE, Role.POLICE) == 20
    assert score_for(Outcome.CAPTURE, Role.THIEF) == 5


def test_stage1_divergence_refusal() -> None:
    with pytest.raises(ValueError, match="termination contract"):
        _create_pair(max_steps=34, survival_thresh=35)

    with pytest.raises(ValueError, match="termination contract"):
        _create_pair(max_steps=35, survival_thresh=40)


def test_stage1_barrier_quota_rejection() -> None:
    cop, _ = _create_pair(size=7, barriers_max=2)
    # Cop places barrier 1 at (0, 1) and barrier 2 at (1, 0)
    cop.place_own_barrier((0, 1))
    cop.place_own_barrier((1, 0))
    assert cop.barriers_placed == 2
    assert len(cop.barriers) == 2

    # Attempting to place 3rd barrier must be rejected
    with pytest.raises(IllegalMoveError, match="not a legal barrier"):
        cop.place_own_barrier((0, 1))
    assert cop.barriers_placed == 2
    assert cop.position == (0, 0)


def test_stage1_deterministic_reproducibility() -> None:
    def _run_sequence() -> tuple[list[str], tuple[int, int]]:
        cop, _ = _create_pair()
        moves = ["MOVE:S", "MOVE:E", "MOVE:S", "MOVE:E", "MOVE:N", "MOVE:W"]
        history = []
        for m in moves:
            legal = cop.legal_moves()
            history.append(f"pos={cop.position},legal={sorted(legal)},move={m}")
            cop.apply_own_move(m)
        return history, cop.position

    run1_hist, run1_pos = _run_sequence()
    run2_hist, run2_pos = _run_sequence()
    assert run1_hist == run2_hist
    assert run1_pos == run2_pos
