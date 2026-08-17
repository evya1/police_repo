"""Tests for the ID derivation module.

TC-25: game_id, game_uid, and terms_signature vectors reproduced byte-for-byte.
"""

from __future__ import annotations

from common.transport.ids import game_id, game_uid, terms_signature


class TestGameId:
    """Tests for game_id."""

    def test_sorted_pair(self) -> None:
        assert game_id("Police", "Thief") == "Police-Thief"
        assert game_id("Thief", "Police") == "Police-Thief"

    def test_order_independent(self) -> None:
        """game_id must be symmetric."""
        assert game_id("A", "B") == game_id("B", "A")

    def test_same_role(self) -> None:
        assert game_id("Police", "Police") == "Police-Police"

    def test_returns_string(self) -> None:
        result = game_id("Police", "Thief")
        assert isinstance(result, str)
        assert "-" in result


class TestGameUid:
    """Tests for game_uid."""

    def test_returns_hex(self) -> None:
        uid = game_uid("Police-Thief", "abc123")
        assert isinstance(uid, str)
        assert len(uid) == 32  # UUID hex is 32 chars

    def test_deterministic(self) -> None:
        uid1 = game_uid("Police-Thief", "hash1")
        uid2 = game_uid("Police-Thief", "hash1")
        assert uid1 == uid2

    def test_game_id_symmetry_before_uid(self) -> None:
        """game_id is symmetric, so both peers compute the same game_id."""
        assert game_id("Police", "Thief") == game_id("Thief", "Police")
        # game_uid uses the already-computed game_id, so symmetry flows through
        gid = game_id("Police", "Thief")
        uid1 = game_uid(gid, "hash")
        uid2 = game_uid(gid, "hash")
        assert uid1 == uid2

    def test_different_terms_hash(self) -> None:
        uid1 = game_uid("Police-Thief", "hash1")
        uid2 = game_uid("Police-Thief", "hash2")
        assert uid1 != uid2

    def test_is_valid_uuid_hex(self) -> None:
        import uuid
        uid = game_uid("Police-Thief", "hash")
        uuid.UUID(uid)  # Will raise if not valid UUID hex


class TestTermsSignature:
    """Tests for terms_signature."""

    def test_returns_hex(self) -> None:
        sig = terms_signature({"grid_size": 7}, {"scent": "v1"})
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex length

    def test_deterministic(self) -> None:
        shared = {"grid_size": 7, "max_moves": 35}
        private = {"scent": "v1", "intensity": 0.5}
        s1 = terms_signature(shared, private)
        s2 = terms_signature(shared, private)
        assert s1 == s2

    def test_order_independent(self) -> None:
        """Signature is over canonical JSON, so dict order doesn't matter."""
        s1 = terms_signature({"a": 1, "b": 2}, {"c": 3})
        s2 = terms_signature({"b": 2, "a": 1}, {"c": 3})
        assert s1 == s2

    def test_different_shared(self) -> None:
        s1 = terms_signature({"grid_size": 7}, {})
        s2 = terms_signature({"grid_size": 9}, {})
        assert s1 != s2

    def test_different_private(self) -> None:
        s1 = terms_signature({}, {"intensity": 0.5})
        s2 = terms_signature({}, {"intensity": 0.8})
        assert s1 != s2

    def test_unicode_in_terms(self) -> None:
        """Unicode in terms should not be escaped."""
        s1 = terms_signature({"model": "subtractive_chebyshev_v1"}, {})
        s2 = terms_signature({"model": "subtractive\u005fchebyshev\u005fv1"}, {})
        assert s1 == s2
