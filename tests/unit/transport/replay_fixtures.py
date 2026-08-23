"""Shared builders for replay record/verify tests: honest steps, tamper helpers, doc shape.

Kept here (not in either test module) so both ``test_replay_records.py`` and
``test_replay_verify.py`` stay under the 150 logical-line cap.
"""

from __future__ import annotations

from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce

GAME_ID = "A-vs-B"
GAME_UID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SUB_GAME_INDEX = 1
TERMS = {"board_size": 7, "max_steps": 35, "barriers_max": 14, "survival_threshold": 20}


def seal(payload: dict) -> dict:
    """Flat raw record: payload fields expanded to top level, plus nonce/commit."""
    nonce = new_nonce()
    return {**payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}


def nested(payload: dict) -> dict:
    """Nested (kit) raw record: payload kept under its own key."""
    nonce = new_nonce()
    return {"payload": payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}


def reseal(record: dict) -> dict:
    """Recompute commit/nonce for a flat record whose payload fields were mutated in place.

    Use this for physics-violation fixtures so the commitment stays intact and the failure
    is attributable to physics, not to a hash mismatch.
    """
    payload = {k: v for k, v in record.items() if k not in ("nonce", "commit")}
    nonce = new_nonce()
    return {**payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}


def honest_steps(
    n: int = 3,
    sender: str = "thief",
    intent: str = "evade",
    start: tuple[int, int] = (3, 3),
    builder=seal,
) -> list[dict]:
    """``n`` honestly sealed steps after a step-0 declaration, walking south/east from start."""
    steps = [builder({"step": 0, "sender": sender, "intent": "declare"})]
    r, c = start
    for i in range(1, n + 1):
        if i % 2:
            r += 1
            move = "MOVE:S"
        else:
            c += 1
            move = "MOVE:E"
        steps.append(
            builder(
                {
                    "step": i,
                    "sender": sender,
                    "intent": intent,
                    "state": f"grid=7x7;self=[{r}, {c}];barriers=[]",
                    "move": move,
                    "hint": "hint",
                }
            )
        )
    return steps


def make_log_doc(
    own: list[dict],
    opp: list[dict] | None = None,
    *,
    game_id: str = GAME_ID,
    game_uid: str = GAME_UID,
    sub_game_index: int = SUB_GAME_INDEX,
    **extra: object,
) -> dict:
    doc: dict = {
        "game_id": game_id,
        "game_uid": game_uid,
        "sub_game_index": sub_game_index,
        "records": own,
        **extra,
    }
    if opp is not None:
        doc["opponent_records"] = opp
    return doc


def steps_with_step_values(step_values: list[int]) -> list[dict]:
    """Minimal sealed records at the given (possibly broken) step values, for sequence tests."""
    return [seal({"step": s, "sender": "thief", "intent": "evade"}) for s in step_values]


def off_board(own: list[dict]) -> list[dict]:
    own[1] = reseal({**own[1], "state": "grid=7x7;self=[9, 9];barriers=[]"})
    return own


def jump_step(own: list[dict]) -> list[dict]:
    own[2] = reseal({**own[2], "state": "grid=7x7;self=[6, 5];barriers=[]"})
    return own


def barrier_quota(own: list[dict]) -> list[dict]:
    barriers = str([[i, i] for i in range(15)])
    own[1] = reseal({**own[1], "state": f"grid=7x7;self=[4, 3];barriers={barriers}"})
    return own


def role_wrong_capture_claim(own: list[dict]) -> list[dict]:
    own[1] = reseal({**own[1], "sender": "police", "win_claim": {"type": "capture"}})
    return own


def make_config_doc(
    *,
    game_id: str = GAME_ID,
    game_uid: str = GAME_UID,
    sub_game_index: int = SUB_GAME_INDEX,
    terms: dict | None = None,
) -> dict:
    return {
        "game_id": game_id,
        "game_uid": game_uid,
        "sub_game_index": sub_game_index,
        "terms": TERMS if terms is None else terms,
    }
