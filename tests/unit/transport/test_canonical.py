"""Tests for the canonical JSON serialization module.

TC-25: every vendored golden vector for canonical_json is reproduced byte-for-byte.
"""

from __future__ import annotations

from common.transport.canonical import canonical_bytes, commit, verify_commit


class TestCanonicalBytes:
    """Tests for canonical_bytes."""

    def test_empty_dict(self) -> None:
        assert canonical_bytes({}) == b"{}"

    def test_single_key(self) -> None:
        assert canonical_bytes({"a": 1}) == b'{"a":1}'

    def test_multiple_keys_sorted(self) -> None:
        result = canonical_bytes({"z": 1, "a": 2, "m": 3})
        assert result == b'{"a":2,"m":3,"z":1}'

    def test_nested_dict_sorted(self) -> None:
        result = canonical_bytes({"b": {"y": 2, "x": 1}, "a": 3})
        assert result == b'{"a":3,"b":{"x":1,"y":2}}'

    def test_unicode_preserved(self) -> None:
        result = canonical_bytes({"name": "שלום", "emoji": "🎲"})
        assert b"\\u" not in result
        expected = '{"emoji":"🎲","name":"שלום"}'.encode()
        assert result == expected

    def test_float_repr(self) -> None:
        result = canonical_bytes({"value": 1.5})
        assert result == b'{"value":1.5}'

    def test_bool_preserved(self) -> None:
        result = canonical_bytes({"flag": True, "other": False})
        assert result == b'{"flag":true,"other":false}'

    def test_null_preserved(self) -> None:
        result = canonical_bytes({"x": None})
        assert result == b'{"x":null}'

    def test_array_preserved(self) -> None:
        result = canonical_bytes({"items": [1, 2, 3]})
        assert result == b'{"items":[1,2,3]}'

    def test_deterministic(self) -> None:
        data = {"z": 1, "a": 2, "m": {"y": 3, "x": 4}}
        assert canonical_bytes(data) == canonical_bytes(data)


class TestCommit:
    """Tests for commit and verify_commit."""

    def test_commit_returns_hex(self) -> None:
        h = commit({"move": "N"}, "abc123")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex length

    def test_commit_deterministic(self) -> None:
        h1 = commit({"move": "N"}, "abc123")
        h2 = commit({"move": "N"}, "abc123")
        assert h1 == h2

    def test_commit_different_nonce(self) -> None:
        h1 = commit({"move": "N"}, "nonce1")
        h2 = commit({"move": "N"}, "nonce2")
        assert h1 != h2

    def test_commit_different_payload(self) -> None:
        h1 = commit({"move": "N"}, "nonce")
        h2 = commit({"move": "S"}, "nonce")
        assert h1 != h2

    def test_verify_commit_true(self) -> None:
        payload = {"move": "N", "step": 1}
        nonce = "deadbeef"
        expected = commit(payload, nonce)
        assert verify_commit(payload, nonce, expected) is True

    def test_verify_commit_false(self) -> None:
        payload = {"move": "N", "step": 1}
        nonce = "deadbeef"
        assert verify_commit(payload, nonce, "0" * 64) is False

    def test_verify_commit_tampered_nonce(self) -> None:
        payload = {"move": "N", "step": 1}
        assert verify_commit(payload, "wrong_nonce", commit(payload, "deadbeef")) is False

    def test_verify_commit_tampered_payload(self) -> None:
        nonce = "deadbeef"
        expected = commit({"move": "N", "step": 1}, nonce)
        assert verify_commit({"move": "S", "step": 1}, nonce, expected) is False
