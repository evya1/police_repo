"""Tests for strict record decoding (replay_records.py).

TC-RP-06: nested and flat encodings of the same payload decode to an identical SealedRecord.
TC-RP-09: step-0 declaration records decode and are classified foreign (no state string).
"""

from __future__ import annotations

import pytest

from common.transport.canonical import canonical_bytes
from common.transport.canonical import commit as hash_commit
from common.transport.replay_records import (
    RecordDecodeError,
    decode_half,
    decode_record,
    is_foreign_record,
)
from tests.unit.transport.replay_fixtures import honest_steps, seal


def _raw_pair(payload: dict) -> tuple[dict, dict]:
    nonce = "a" * 32
    commit = hash_commit(payload, nonce)
    flat = {**payload, "nonce": nonce, "commit": commit}
    kit = {"payload": payload, "nonce": nonce, "commit": commit}
    return flat, kit


class TestShapeEquivalence:
    def test_flat_and_nested_decode_identically(self) -> None:
        payload = {"step": 2, "sender": "police", "intent": "chase", "state": "s", "move": "MOVE:S"}
        flat, kit = _raw_pair(payload)
        assert decode_record(flat) == decode_record(kit)

    def test_payload_bytes_is_canonical(self) -> None:
        payload = {"step": 1, "sender": "thief", "intent": "evade"}
        flat, _ = _raw_pair(payload)
        assert decode_record(flat).payload_bytes == canonical_bytes(payload)

    def test_step_0_decodes_and_is_foreign(self) -> None:
        flat = seal({"step": 0, "sender": "thief", "intent": "declare"})
        rec = decode_record(flat)
        assert rec.step == 0
        payload = {k: v for k, v in flat.items() if k not in ("nonce", "commit")}
        assert is_foreign_record(payload) is True


class TestDecodeRecordRejects:
    @pytest.mark.parametrize("bad_step", [True, False, -1, "1", None, 1.5])
    def test_bad_step(self, bad_step: object) -> None:
        flat, _ = _raw_pair({"step": bad_step})
        with pytest.raises(RecordDecodeError) as exc:
            decode_record(flat)
        assert exc.value.code == "bad_step"

    @pytest.mark.parametrize("bad_nonce", ["", None, 7])
    def test_bad_nonce(self, bad_nonce: object) -> None:
        flat, _ = _raw_pair({"step": 1})
        flat["nonce"] = bad_nonce
        with pytest.raises(RecordDecodeError) as exc:
            decode_record(flat)
        assert exc.value.code == "bad_nonce"

    @pytest.mark.parametrize("bad_commit", ["ABCD" * 16, "a" * 63, "not-hex" * 8, None, 5])
    def test_bad_commitment(self, bad_commit: object) -> None:
        flat, _ = _raw_pair({"step": 1})
        flat["commit"] = bad_commit
        with pytest.raises(RecordDecodeError) as exc:
            decode_record(flat)
        assert exc.value.code == "bad_commitment"

    def test_unknown_shape(self) -> None:
        with pytest.raises(RecordDecodeError) as exc:
            decode_record({"nonce": "a" * 32, "commit": "b" * 64})
        assert exc.value.code == "unknown_shape"

    def test_nested_payload_not_a_dict(self) -> None:
        with pytest.raises(RecordDecodeError) as exc:
            decode_record({"payload": "nope", "nonce": "a" * 32, "commit": "b" * 64})
        assert exc.value.code == "bad_payload"


class TestDecodeHalf:
    def test_empty_is_clean(self) -> None:
        assert decode_half([], "own") == ([], [])

    def test_not_a_list(self) -> None:
        _, issues = decode_half({"oops": True}, "own")
        assert [i.code for i in issues] == ["bad_half_shape"]

    def test_mixed_shape_rejected(self) -> None:
        payload = {"step": 1, "sender": "thief", "intent": "evade"}
        flat, kit = _raw_pair(payload)
        _, issues = decode_half([flat, kit], "own")
        assert [i.code for i in issues] == ["mixed_shape"]

    def test_duplicate_step(self) -> None:
        recs = [seal({"step": 0}), seal({"step": 1}), seal({"step": 1})]
        _, issues = decode_half(recs, "own")
        assert "duplicate_step" in [i.code for i in issues]

    def test_out_of_order_step(self) -> None:
        recs = [seal({"step": 0}), seal({"step": 2}), seal({"step": 1})]
        _, issues = decode_half(recs, "own")
        assert "out_of_order_step" in [i.code for i in issues]

    def test_skipped_step(self) -> None:
        recs = [seal({"step": 0}), seal({"step": 1}), seal({"step": 3})]
        _, issues = decode_half(recs, "own")
        assert [i.code for i in issues] == ["skipped_step"]

    def test_malformed_record_reported_with_half(self) -> None:
        bad = seal({"step": -1})
        _, issues = decode_half([bad], "opponent")
        assert issues[0].code == "bad_step"
        assert issues[0].half == "opponent"

    def test_honest_sequence_clean(self) -> None:
        records, issues = decode_half(honest_steps(3), "own")
        assert issues == []
        assert [r.step for r in records] == [0, 1, 2, 3]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"state": "grid=7x7;self=[3, 3];barriers=[]", "move": "MOVE:N"}, False),
        ({"state": "grid=7x7;self=[0, 0];barriers=[[1, 1]]", "move": "MOVE:S"}, False),
        ({"state": "grid=7x7;self=[-1, -1];barriers=[]", "move": "MOVE:S"}, False),
        ({"move": "MOVE:N"}, True),
        ({"state": "", "move": "MOVE:N"}, True),
        ({"position": [3, 3], "move": "MOVE:N"}, True),
        ({"state": "position=[3,3]", "move": "MOVE:N"}, True),
    ],
)
def test_foreign_detection(payload: dict, expected: bool) -> None:
    assert is_foreign_record(payload) is expected
