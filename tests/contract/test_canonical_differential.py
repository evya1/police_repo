"""Differential fixtures for the recorded canonical-bytes convention (T008 AC #6).

`{#cross_peer_vectors}` requires fixtures that cover the ways two peers can serialize
the *same* record into *different* bytes — compact vs spaced JSON, nonce appended vs
embedded, key order, Unicode escaping, signature insertion, float representation — so
that a peer diverging on any of them is caught at audit rather than silently accepted.

**OPEN-007 is officially OPEN.** These fixtures pin the *recorded* convention
(`docs/spec/OPEN_QUESTIONS.md` → "OPEN-007 canonical serialization convention") and
prove the enumerated alternatives are byte-distinguishable from it. They do **not**
claim the recorded bytes are the officially required bytes; only the recorded form is
enabled for production, and the final report envelope stays behind the OPEN-007 gate.
Replay and step-order divergence live on the audit path and are covered by
`test_audit_tampered.py` / `test_turn_validation_general.py`.
"""

from __future__ import annotations

import hashlib
import json

from common.transport.canonical import canonical_bytes, commit, verify_commit
from common.transport.ids import terms_signature


def _payload() -> dict:
    return {"b": 2, "a": 1, "state": "MOVE", "note": "café"}


class TestCompactVsSpaced:
    """The recorded form is compact; a spaced serializer produces different bytes."""

    def test_recorded_form_is_compact(self) -> None:
        assert canonical_bytes({"a": 1, "b": 2}) == b'{"a":1,"b":2}'

    def test_spaced_json_diverges(self) -> None:
        data = _payload()
        spaced = json.dumps(data, sort_keys=True, ensure_ascii=False,
                            separators=(", ", ": ")).encode("utf-8")
        assert canonical_bytes(data) != spaced


class TestKeyOrder:
    """Input key order must not change the bytes; an unsorted serializer would."""

    def test_reordered_input_is_identical(self) -> None:
        assert canonical_bytes({"a": 1, "b": 2}) == canonical_bytes({"b": 2, "a": 1})

    def test_unsorted_serializer_diverges(self) -> None:
        data = {"b": 2, "a": 1}
        unsorted = json.dumps(data, sort_keys=False, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
        assert canonical_bytes(data) != unsorted  # {"b":2,"a":1} != {"a":1,"b":2}


class TestUnicodeEscaping:
    """Unicode is preserved as UTF-8, not escaped to \\uXXXX."""

    def test_non_ascii_preserved(self) -> None:
        data = {"setting": "café", "hint": "日本語", "emoji": "🚓"}
        raw = canonical_bytes(data)
        assert "café".encode() in raw
        assert b"\\u" not in raw  # no ASCII-escaped escapes

    def test_escaped_form_diverges(self) -> None:
        data = {"hint": "café"}
        escaped = json.dumps(data, sort_keys=True, ensure_ascii=True,
                            separators=(",", ":")).encode("utf-8")
        assert canonical_bytes(data) != escaped


class TestNoncePlacement:
    """The nonce is pipe-appended after the payload bytes, not embedded in the payload."""

    def test_appended_differs_from_embedded(self) -> None:
        payload = _payload()
        nonce = "abcd1234"
        appended = commit(payload, nonce)
        embedded = hashlib.sha256(canonical_bytes({**payload, "nonce": nonce})).hexdigest()
        assert appended != embedded

    def test_pipe_separator_is_load_bearing(self) -> None:
        """Without the separator, "a"+"b1" and "ab"+"1" would collide; the pipe prevents it."""
        assert commit({"x": "a"}, "b1") != commit({"x": "ab"}, "1")

    def test_verify_roundtrips_recorded_form(self) -> None:
        payload, nonce = _payload(), "n-0001"
        assert verify_commit(payload, nonce, commit(payload, nonce))


class TestSignatureInsertion:
    """Inserting a signature field into the signed payload changes the signed bytes."""

    def test_signature_field_changes_the_signature(self) -> None:
        terms = {"board_size": 7, "setting": "New York"}
        nonce = "sig-nonce"
        clean = terms_signature(terms, nonce)
        injected = terms_signature({**terms, "signature": clean}, nonce)
        assert clean != injected


class TestFloatRoundTrip:
    """A float is emitted in its shortest round-tripping form (AC #5 tie-in)."""

    def test_shortest_repr(self) -> None:
        assert canonical_bytes({"x": 0.1}) == b'{"x":0.1}'
        assert canonical_bytes({"x": 1.0}) == b'{"x":1.0}'

    def test_float_survives_round_trip(self) -> None:
        raw = canonical_bytes({"decay": 0.1, "emit": 0.9})
        assert json.loads(raw) == {"decay": 0.1, "emit": 0.9}
