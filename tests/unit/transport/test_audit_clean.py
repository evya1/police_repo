"""TC-20 (clean): a full mutual audit of honest records passes all three layers.

Layer 1 re-hashes every revealed record with our own serializer; layer 2 binds the
revealed commits to what was actually received in play; layer 3 checks physics from
the signed terms (trail on-board, one orthogonal step, barrier quota, step ceiling).
An honest, sealed, consistent bundle passes all three.
"""

from __future__ import annotations

from common.transport.audit import AuditVerdict, audit_records
from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce

_TERMS = {"board_size": 7, "max_steps": 35, "barriers_max": 14}

# A bounded one-step trail from (3,3): each move is a single orthogonal step, in bounds.
_TRAIL = [
    (4, 3, "MOVE:S"),
    (4, 4, "MOVE:E"),
    (5, 4, "MOVE:S"),
    (5, 3, "MOVE:W"),
    (6, 3, "MOVE:S"),
    (6, 4, "MOVE:E"),
]


def _seal(payload: dict) -> dict:
    """Seal a payload into a record with a fresh nonce and commit."""
    nonce = new_nonce()
    return dict(payload, nonce=nonce, commit=hash_commit(payload, nonce))


def _honest_records(steps: int = 6) -> tuple[list[dict], dict[int, str]]:
    """Build an honest sealed trail (step-0 declaration + `steps` moves) and its played map."""
    records = [_seal({"step": 0, "sender": "thief", "intent": "declare"})]
    played: dict[int, str] = {}
    for step in range(1, steps + 1):
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


def test_clean_audit_passes() -> None:
    records, played = _honest_records(6)
    result = audit_records(records, played, _TERMS)
    assert result.passed is True
    assert result.failed_steps == []
    assert result.tampered_steps == []
    assert result.verified_steps == 6


def test_clean_audit_verdict_is_passed() -> None:
    records, played = _honest_records(3)
    result = audit_records(records, played, _TERMS)
    assert result.verdict == AuditVerdict.PASSED


def test_step_zero_declaration_is_verified_not_counted() -> None:
    records, played = _honest_records(2)
    result = audit_records(records, played, _TERMS)
    # The step-0 identity record re-hashes clean but is not a counted move (FR-19).
    assert result.passed is True
    assert result.verified_steps == 2


def test_empty_records_pass() -> None:
    result = audit_records([], {}, _TERMS)
    assert result.passed is True
    assert result.verified_steps == 0
