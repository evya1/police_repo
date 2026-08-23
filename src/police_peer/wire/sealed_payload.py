"""How a decision becomes the ONE payload this peer seals for a turn (T054).

Split out of ``session.py`` so that module owns only the mutable sub-game lifecycle and
this one owns payload construction. Both wire adapters (`BrainDrivenEngine`,
`StandInEngine`) compose these two functions rather than each keeping a copy: a sealed
payload is evidence, and two copies of it are two places for the kit-required post-move
`position` -- or the concession cell -- to drift apart. A drift between the two engines
would surface only as an opponent's audit failure, at the worst possible moment.

Both functions are the single construction boundary the kit `position` port lands on: the
value is derived once, here, from the engine's own state *after* the action is applied and
*before* the record is committed. It is never appended to the envelope after hashing, and
``PUBLIC_TURN_KEYS`` does not project it, so it reaches neither the opponent's turn message
nor an LLM prompt.
"""

from __future__ import annotations

from typing import Any

from common.domain.board import Cell
from common.domain.scoring import Role
from police_peer.wire.session import SubgameSession


def _own_cell(engine) -> list[int]:
    """This peer's own post-action cell as the kit's `[row, col]`."""
    return [int(engine.position[0]), int(engine.position[1])]


def build_result(
    session: SubgameSession,
    *,
    move: str,
    hint: str,
    verdict: str = "truth",
    fallback: bool = False,
    reasoning: str = "",
    prompt_text: str = "",
    response_seconds: float = 0.0,
    barrier_cell: Cell | None = None,
) -> dict[str, Any]:
    """Build the ONE sealed result for this turn (Decision metadata + own smell_grid +
    claim handling); the wire adapter derives the public projection from it -- never build
    a second outgoing dict.

    The truthful capture exchange (GAME-009/SEC-007) is runtime-owned, not a strategy
    concern: every POLICE non-barrier action turn attaches ``capture_claim`` naming the
    Police's own post-action cell (the Police cannot *know* it captured -- the Thief's
    honest answer resolves it). A barrier turn (``barrier_cell is not None``) forfeits the
    move (GAME-006) and declares ``barrier_placed`` instead; it never also invents a move
    capture claim.
    """
    engine, trail = session.engine, session.trail
    assert engine is not None and trail is not None
    res: dict[str, Any] = {
        "move": move,
        "barrier_cell": list(barrier_cell) if barrier_cell is not None else None,
        "hint": hint,
        "verdict": verdict,
        "fallback": fallback,
        "reasoning": reasoning,
        "prompt_text": prompt_text,
        "response_seconds": response_seconds,
        "state": engine.state_string(),
        # The pinned kit's full artifact physics walker dereferences `payload["position"]`
        # and cannot walk a game without it; `state` spells the same cell but the walker
        # reads both and cross-checks them, so they must be one derivation.
        "position": _own_cell(engine),
        "smell_grid": trail.full_turn(engine.position),
    }
    if barrier_cell is not None:
        # Public, exact declaration (GAME-012): the cop must be truthful about every
        # placement, in the same turn as the STAY that forfeits the move.
        res["barrier_placed"] = list(barrier_cell)
    if engine.role is Role.POLICE and barrier_cell is None:
        res["capture_claim"] = list(engine.position)
    if session.pending_claim is not None:
        ans = engine.answer_capture_claim(session.pending_claim, at=session.pending_claim_position)
        res["claim_response"] = ans
        session.pending_claim = None
        session.pending_claim_position = None
        if ans and ans.get("caught") is True:
            session.thief_caught = True
            res["win_claim"] = {"type": "capture"}
            return res
    if engine.role is Role.THIEF:
        if engine.self_captured():
            res["win_claim"] = {"type": "capture"}
        elif engine.survived():
            res["win_claim"] = {"type": "survival"}
    return res


def build_terminal_final(session: SubgameSession) -> dict[str, Any] | None:
    """Return the sealed game-ending final step this peer owes, or None (rule 35).

    A thief that saw its own capture (rules 46/47 -- a fact only the thief can see) owes a
    concession: a STAY naming its own final cell with ``caught: true``. A police settling
    from the thief's final owes a plain sealed STAY. An answered claim or a survival claim
    already rode the last normal step, so only the invisible capture needs the extra step.
    """
    engine = session.engine
    if engine is None:
        return None
    smell_grid = session.trail.full_turn(engine.position) if session.trail is not None else {}
    is_thief = engine.role is Role.THIEF
    if is_thief and engine.self_captured() is None:
        return None
    if not is_thief and session.terminal() is None:
        return None
    session.apply_move("STAY")
    cell = _own_cell(engine)
    final: dict[str, Any] = {
        "move": "STAY",
        "hint": "",
        "state": engine.state_string(),
        "position": cell,
        "smell_grid": smell_grid,
    }
    if is_thief:
        final["claim_response"] = {"claim": cell, "caught": True}
    return final
