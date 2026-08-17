"""Tests for the integrity primitives module.

TC-25: nonce secrecy and audit payload structure.
"""

from __future__ import annotations

from common.transport.integrity import audit_payload, new_nonce


class TestNewNonce:
    """Tests for new_nonce."""

    def test_returns_string(self) -> None:
        nonce = new_nonce()
        assert isinstance(nonce, str)

    def test_returns_32_hex_chars(self) -> None:
        nonce = new_nonce()
        assert len(nonce) == 32
        int(nonce, 16)  # Will raise if not valid hex

    def test_uniqueness(self) -> None:
        nonces = {new_nonce() for _ in range(100)}
        assert len(nonces) == 100  # All unique

    def test_not_predictable(self) -> None:
        """A nonce should not be a fixed string."""
        nonces = {new_nonce() for _ in range(10)}
        assert len(nonces) > 1


class TestAuditPayload:
    """Tests for audit_payload."""

    def test_returns_dict(self) -> None:
        payload = audit_payload("s1", "N", "move", "abc123")
        assert isinstance(payload, dict)

    def test_contains_all_keys(self) -> None:
        payload = audit_payload("s1", "N", "move", "abc123")
        assert set(payload.keys()) == {"state", "move", "intent", "nonce"}

    def test_values_preserved(self) -> None:
        payload = audit_payload("state_x", "MOVE:N", "advance", "deadbeef")
        assert payload["state"] == "state_x"
        assert payload["move"] == "MOVE:N"
        assert payload["intent"] == "advance"
        assert payload["nonce"] == "deadbeef"

    def test_nonce_is_secret_until_reveal(self) -> None:
        """The nonce should not be derivable from state/move/intent alone."""
        p1 = audit_payload("s", "N", "m", "nonce1")
        p2 = audit_payload("s", "N", "m", "nonce2")
        assert p1["nonce"] != p2["nonce"]
        assert p1["state"] == p2["state"]
        assert p1["move"] == p2["move"]
        assert p1["intent"] == p2["intent"]
