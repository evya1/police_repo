"""Tests for the replay shape adapter (replay_records.py).

TC-RP-06: differential round-trip identity over a fixture sweep.
TC-RP-09: step-0 handling — declaration record round-trips correctly.
"""

from __future__ import annotations

import pytest

from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce
from common.transport.replay_records import (
    flat_steps_to_kit_doc,
    from_kit_record,
    is_foreign_record,
    to_kit_record,
)


def _flat(step: int, sender: str, intent: str, **extra: object) -> dict:
    nonce = new_nonce()
    payload = {"step": step, "sender": sender, "intent": intent, **extra}
    return {**payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}


def _steps(n: int = 3) -> list[dict]:
    steps = [_flat(0, "thief", "declare")]
    for i in range(1, n + 1):
        steps.append(_flat(i, "thief", "evade",
                          state=f"grid=7x7;self=[{i}, {i}];barriers=[]",
                          move=f"MOVE:{"N" if i % 2 else "E"}", hint="hint"))
    return steps


def _opp_steps(n: int = 2) -> list[dict]:
    steps = [_flat(0, "police", "declare")]
    for i in range(1, n + 1):
        steps.append(_flat(i, "police", "chase",
                          state=f"grid=7x7;self=[0, {i}];barriers=[]",
                          move=f"MOVE:{"E" if i % 2 else "S"}", hint="hint"))
    return steps


# TC-RP-06 + TC-RP-09: round-trip identity (including step-0)
class TestRoundTripIdentity:
    @pytest.mark.parametrize(("step", "sender", "intent", "extra"), [
        (0, "thief", "declare", {}),
        (1, "thief", "evade", {"state": "grid=7x7;self=[1, 1];barriers=[]", "move": "MOVE:N", "hint": "north"}),
        (2, "police", "chase", {"state": "grid=7x7;self=[2, 2];barriers=[]", "move": "MOVE:S"}),
        (3, "thief", "evade", {"state": "grid=7x7;self=[3, 3];barriers=[[1,1],[2,2]]",
                               "move": "MOVE:W", "hint": "west", "barrier_placed": True}),
    ])
    def test_round_trip(self, step: int, sender: str, intent: str, extra: dict) -> None:
        flat = _flat(step, sender, intent, **extra)
        assert from_kit_record(to_kit_record(flat)) == flat

    def test_preserves_commit(self) -> None:
        flat = _flat(2, "police", "chase", state="grid=7x7;self=[2, 2];barriers=[]", move="MOVE:S")
        back = from_kit_record(to_kit_record(flat))
        assert back["commit"] == flat["commit"]
        assert back["nonce"] == flat["nonce"]
        assert hash_commit({k: v for k, v in back.items() if k not in ("nonce", "commit")},
                           back["nonce"]) == back["commit"]

    def test_fixture_sweep(self) -> None:
        for flat in _steps(5):
            assert from_kit_record(to_kit_record(flat)) == flat

    def test_fixture_sweep_opponent(self) -> None:
        for flat in _opp_steps(4):
            assert from_kit_record(to_kit_record(flat)) == flat

    def test_step_0_is_foreign(self) -> None:
        """Step-0 has no state string — it is foreign by the adapter's definition."""
        assert is_foreign_record(to_kit_record(_flat(0, "thief", "declare"))["payload"]) is True

    def test_step_0_round_trips(self) -> None:
        flat = _flat(0, "thief", "declare")
        back = from_kit_record(to_kit_record(flat))
        assert back["step"] == 0
        assert back["sender"] == "thief"
        assert back["intent"] == "declare"
        assert back["commit"] == flat["commit"]

    def test_step_0_rehashes(self) -> None:
        back = from_kit_record(to_kit_record(_flat(0, "thief", "declare")))
        assert hash_commit({k: v for k, v in back.items() if k not in ("nonce", "commit")},
                           back["nonce"]) == back["commit"]


# flat_steps_to_kit_doc
def test_records_only() -> None:
    doc = flat_steps_to_kit_doc(_steps(2), None)
    assert len(doc["records"]) == 3
    assert "opponent_records" not in doc


def test_both_halves() -> None:
    doc = flat_steps_to_kit_doc(_steps(2), _opp_steps(1))
    assert len(doc["records"]) == 3
    assert len(doc["opponent_records"]) == 2


def test_kit_records_nested() -> None:
    rec = flat_steps_to_kit_doc(_steps(1), None)["records"][0]
    assert "payload" in rec
    assert "nonce" in rec
    assert "commit" in rec
    assert "step" not in rec


# is_foreign_record
@pytest.mark.parametrize(("payload", "expected"), [
    ({"state": "grid=7x7;self=[3, 3];barriers=[]", "move": "MOVE:N"}, False),
    ({"state": "grid=7x7;self=[0, 0];barriers=[[1, 1]]", "move": "MOVE:S"}, False),
    ({"state": "grid=7x7;self=[-1, -1];barriers=[]", "move": "MOVE:S"}, False),
    ({"move": "MOVE:N"}, True),
    ({"state": "", "move": "MOVE:N"}, True),
    ({"position": [3, 3], "move": "MOVE:N"}, True),
    ({"state": "position=[3,3]", "move": "MOVE:N"}, True),
])
def test_foreign_detection(payload: dict, expected: bool) -> None:
    assert is_foreign_record(payload) is expected
