"""Failing-first tests: the runtime-owned truthful capture exchange.

Items 4/5 of the repair task's required tests: every Police non-barrier
action turn attaches ``capture_claim`` naming its own post-action position; a
barrier turn never also invents one; a Thief answers a claim from the
position that existed WHEN IT ARRIVED, not after its own next move (the
"move away, then deny" defect).
"""

from __future__ import annotations

from common.domain.scoring import Role
from police_peer.wire.brain import BrainDrivenEngine
from police_peer.wire.session import SubgameSession

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}


def test_non_barrier_move_attaches_own_position_as_capture_claim() -> None:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    result = engine.decide()
    if result.get("barrier_placed") is None:
        assert result.get("capture_claim") == list(engine._session.engine.position)


def test_barrier_turn_never_also_carries_a_capture_claim() -> None:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    saw_barrier_turn = False
    for _ in range(20):
        result = engine.decide()
        if result.get("barrier_placed") is not None:
            assert "capture_claim" not in result
            saw_barrier_turn = True
            break
    assert saw_barrier_turn, "seed produced no barrier turn to exercise the guard"


def test_legal_stay_without_barrier_still_carries_capture_claim() -> None:
    """A pursuit-chosen STAY (not a barrier forfeit) is still a non-barrier action turn."""
    session = SubgameSession(natural_role=Role.POLICE, board_size=7, seed=1)
    session.start(1, Role.POLICE, terms=_TERMS)
    session.apply_move("STAY")
    result = session.build_result(move="STAY", hint="holding", barrier_cell=None)
    assert "barrier_placed" not in result
    assert result["capture_claim"] == list(session.engine.position)


def test_thief_answers_claim_from_position_when_it_arrived_not_after_moving() -> None:
    """Move-away-then-deny must be impossible: the answer is judged pre-move."""
    session = SubgameSession(natural_role=Role.THIEF, board_size=7, seed=1)
    session.start(1, Role.THIEF, terms=_TERMS)
    pre_move_position = list(session.engine.position)

    session.observe_barrier_and_claims({"capture_claim": pre_move_position})
    assert session.pending_claim_position == tuple(pre_move_position)

    legal = session.engine.legal_moves()
    move = next((m for m in legal if m != "STAY"), "STAY")
    session.apply_move(move)

    result = session.build_result(move=move, hint="")
    assert result["claim_response"] == {"claim": pre_move_position, "caught": True}


def test_thief_legitimately_denies_a_claim_that_misses() -> None:
    session = SubgameSession(natural_role=Role.THIEF, board_size=7, seed=1)
    session.start(1, Role.THIEF, terms=_TERMS)
    wrong_cell = [6, 6]
    session.observe_barrier_and_claims({"capture_claim": wrong_cell})
    session.apply_move("STAY")
    result = session.build_result(move="STAY", hint="")
    assert result["claim_response"] == {"claim": wrong_cell, "caught": False}
    assert "win_claim" not in result
