"""TC-20 (tampered): one byte of mutation in a revealed record ⇒ TAMPERED.

The iron rule (FR-29): a single re-hash miss is a total sanction — both sides zeroed,
and no code path repairs it. These tests seal an honest bundle, then break it one way
at a time (re-hash miss, equivocation, dropped commit, empty intent) and assert the
audit names the step and the sanction zeroes both sides.
"""

from __future__ import annotations

from common.transport.audit import AuditVerdict, audit_records, tampered_sanction
from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce

_TERMS = {"board_size": 7, "max_steps": 35, "barriers_max": 14}
_TRAIL = [
    (4, 3, "MOVE:S"),
    (4, 4, "MOVE:E"),
    (5, 4, "MOVE:S"),
]


def _seal(payload: dict) -> dict:
    nonce = new_nonce()
    return dict(payload, nonce=nonce, commit=hash_commit(payload, nonce))


def _records_and_played() -> tuple[list[dict], dict[int, str]]:
    records = [_seal({"step": 0, "sender": "thief", "intent": "declare"})]
    played: dict[int, str] = {}
    for step in range(1, 4):
        row, col, move = _TRAIL[step - 1]
        payload = {
            "step": step,
            "sender": "thief",
            "move": move,
            "hint": "here",
            "state": f"grid=7x7;self=[{row}, {col}];barriers=[]",
            "intent": "evade",
        }
        record = _seal(payload)
        records.append(record)
        played[step] = record["commit"]
    return records, played


def test_one_byte_mutation_is_tampered() -> None:
    records, played = _records_and_played()
    records[2]["state"] = records[2]["state"].replace("self=[4, 4]", "self=[4, 5]")
    result = audit_records(records, played, _TERMS)
    assert result.passed is False
    assert 2 in result.tampered_steps
    assert result.verdict == AuditVerdict.TAMPERED


def test_rehash_miss_is_tampered_not_binding() -> None:
    """Change a sealed field: the re-hash misses while the commit stays as received."""
    records, played = _records_and_played()
    records[1]["move"] = "MOVE:W"
    result = audit_records(records, played, _TERMS)
    assert result.passed is False
    assert 1 in result.tampered_steps


def test_equivocation_is_tampered() -> None:
    """A different commit for a played step (layer 2) is tampering, not a slip."""
    records, played = _records_and_played()
    played[3] = "f" * 64
    result = audit_records(records, played, _TERMS)
    assert result.passed is False
    assert 3 in result.tampered_steps


def test_missing_commit_is_tampered() -> None:
    records, played = _records_and_played()
    del records[1]["commit"]
    result = audit_records(records, played, _TERMS)
    assert result.passed is False
    assert 1 in result.tampered_steps


def test_empty_intent_is_tampered() -> None:
    """The intent field must be declared in sealed records (FR-42)."""
    records, played = _records_and_played()
    records[2]["intent"] = " "
    result = audit_records(records, played, _TERMS)
    assert result.passed is False
    assert 2 in result.tampered_steps


def test_tampered_sanction_zeroes_both_sides() -> None:
    """FR-29: the sanction is (police, thief) = (0, 0) — total, no repair path."""
    assert tampered_sanction() == (0, 0)


def test_withheld_reveal_is_tampered() -> None:
    """Revealing nothing for a sub-game that was played is a sanction, not a pass.

    An audit that verifies only the records it is handed lets a peer skip its reveal
    entirely and still settle clean, which would make TAMPER_FORFEIT opt-in.
    """
    _, played = _records_and_played()
    result = audit_records([], played, _TERMS)
    assert result.passed is False
    assert sorted(result.tampered_steps) == [1, 2, 3]


def test_partial_reveal_hiding_the_tampered_step_is_tampered() -> None:
    """Dropping the one record that would fail re-hash must not buy a clean audit."""
    records, played = _records_and_played()
    records[2]["state"] = records[2]["state"].replace("self=[4, 4]", "self=[4, 5]")
    withheld = [r for r in records if int(r.get("step", -1)) != 2]
    result = audit_records(withheld, played, _TERMS)
    assert result.passed is False
    assert 2 in result.tampered_steps


def test_capture_claim_that_misses_is_legal_play() -> None:
    """The cop cannot see the thief, so a claim on the wrong cell is an ordinary miss.

    Only the thief's answer, checked against its own sealed state, is tamper evidence.
    """
    cop_records = [
        _seal(
            {
                "step": 1,
                "sender": "police",
                "move": "STAY",
                "capture_claim": [0, 0],
                "state": "grid=7x7;self=[0, 0];barriers=[]",
                "intent": "pursue",
            }
        )
    ]
    played = {1: cop_records[0]["commit"]}
    thief_records = [
        _seal(
            {
                "step": 1,
                "sender": "thief",
                "move": "STAY",
                "state": "grid=7x7;self=[6, 6];barriers=[]",
                "intent": "evade",
            }
        )
    ]
    result = audit_records(cop_records, played, _TERMS, our_records=thief_records)
    assert result.passed is True
    assert result.failed_steps == []
