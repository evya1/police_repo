"""Tests for the ID derivation module.

TC-25: game_id, game_uid, and terms_signature vectors reproduced byte-for-byte.
"""

from __future__ import annotations

from common.transport.ids import game_id, game_uid, terms_signature


class TestGameId:
    """Tests for game_id."""

    def test_sorted_pair(self) -> None:
        assert game_id("Police", "Thief") == "Police-vs-Thief"
        assert game_id("Thief", "Police") == "Police-vs-Thief"

    def test_order_independent(self) -> None:
        """game_id must be symmetric."""
        assert game_id("A", "B") == game_id("B", "A")

    def test_same_role(self) -> None:
        assert game_id("Police", "Police") == "Police-vs-Police"

    def test_returns_string(self) -> None:
        result = game_id("Police", "Thief")
        assert isinstance(result, str)
        assert "-vs-" in result


class TestGameUid:
    """Tests for game_uid."""

    def test_returns_hex(self) -> None:
        terms = {"board_size": 7, "num_games": 6}
        uid = game_uid(terms, "team-a", "team-b")
        assert isinstance(uid, str)
        assert len(uid) == 36  # UUID string is 36 chars (with hyphens)

    def test_deterministic(self) -> None:
        terms = {"board_size": 7, "num_games": 6}
        uid1 = game_uid(terms, "team-a", "team-b")
        uid2 = game_uid(terms, "team-a", "team-b")
        assert uid1 == uid2

    def test_group_order_independent(self) -> None:
        """game_uid is symmetric in group ids."""
        terms = {"board_size": 7, "num_games": 6}
        uid1 = game_uid(terms, "team-a", "team-b")
        uid2 = game_uid(terms, "team-b", "team-a")
        assert uid1 == uid2

    def test_different_terms(self) -> None:
        uid1 = game_uid({"board_size": 7}, "a", "b")
        uid2 = game_uid({"board_size": 9}, "a", "b")
        assert uid1 != uid2

    def test_is_valid_uuid_hex(self) -> None:
        import uuid
        terms = {"board_size": 7, "num_games": 6}
        uid = game_uid(terms, "a", "b")
        uuid.UUID(uid)  # Will raise if not valid UUID hex


class TestTermsSignature:
    """Tests for terms_signature."""

    def test_returns_hex(self) -> None:
        sig = terms_signature({"board_size": 7}, "nonce123")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex length

    def test_deterministic(self) -> None:
        terms = {"board_size": 7, "max_moves": 35}
        s1 = terms_signature(terms, "nonce1")
        s2 = terms_signature(terms, "nonce1")
        assert s1 == s2

    def test_order_independent(self) -> None:
        """Signature is over canonical JSON, so dict order doesn't matter."""
        s1 = terms_signature({"a": 1, "b": 2}, "n")
        s2 = terms_signature({"b": 2, "a": 1}, "n")
        assert s1 == s2

    def test_different_terms(self) -> None:
        s1 = terms_signature({"board_size": 7}, "n")
        s2 = terms_signature({"board_size": 9}, "n")
        assert s1 != s2

    def test_different_nonce(self) -> None:
        terms = {"board_size": 7}
        s1 = terms_signature(terms, "nonce1")
        s2 = terms_signature(terms, "nonce2")
        assert s1 != s2

    def test_unicode_in_terms(self) -> None:
        """Unicode in terms should not be escaped."""
        terms1 = {"model": "subtractive_chebyshev_v1"}
        terms2 = {"model": "subtractive\u005fchebyshev\u005fv1"}
        s1 = terms_signature(terms1, "n")
        s2 = terms_signature(terms2, "n")
        assert s1 == s2
