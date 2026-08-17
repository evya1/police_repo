"""Tests for lock families and lock decision logic.

FR-16: refuse only when both peers declare a family and the hashes disagree.
Omission on either side is silence, not refusal.
"""

from __future__ import annotations

import pytest

from common.transport.locks import (
    LOCK_DOC_KEYS,
    LOCK_FAMILIES,
    build_lock_doc,
    lock_decision,
    lock_hash,
)


class TestLockFamilies:
    """LOCK_FAMILIES must contain exactly the four known families."""

    def test_contains_expected_families(self) -> None:
        expected = {"scent_model", "wire_shape", "info_mode", "smell_binding"}
        assert expected == LOCK_FAMILIES

    def test_is_frozenset(self) -> None:
        assert isinstance(LOCK_FAMILIES, frozenset)

    def test_has_four_families(self) -> None:
        assert len(LOCK_FAMILIES) == 4


class TestLockDocKeys:
    """LOCK_DOC_KEYS must contain exactly the four canonical keys."""

    def test_contains_expected_keys(self) -> None:
        assert LOCK_DOC_KEYS == ("example", "family", "name", "params")

    def test_is_tuple(self) -> None:
        assert isinstance(LOCK_DOC_KEYS, tuple)


class TestLockDecision:
    """Tests for lock_decision — the refusal rule per SPEC section 7."""

    def test_both_none_is_silence(self) -> None:
        assert lock_decision(None, None) == "silence"

    def test_ours_none_is_silence(self) -> None:
        assert lock_decision(None, "abc") == "silence"

    def test_theirs_none_is_silence(self) -> None:
        assert lock_decision("abc", None) == "silence"

    def test_same_hash_is_accept(self) -> None:
        assert lock_decision("abc123", "abc123") == "accept"

    def test_different_hash_is_refuse(self) -> None:
        assert lock_decision("abc", "def") == "refuse"

    def test_empty_string_vs_none_is_silence(self) -> None:
        # Empty string is a valid (if unusual) declaration — it is not None.
        assert lock_decision("", None) == "silence"
        assert lock_decision("", "") == "accept"

    def test_empty_string_vs_different_is_refuse(self) -> None:
        assert lock_decision("", "abc") == "refuse"


class TestLockHash:
    """Tests for lock_hash — canonical SHA-256 over a lock document."""

    def test_returns_64_char_hex(self) -> None:
        doc = build_lock_doc("scent_model", "v1", {}, {})
        h = lock_hash(doc)
        assert isinstance(h, str)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self) -> None:
        doc = build_lock_doc("wire_shape", "v2", {"grid": 5}, {})
        h1 = lock_hash(doc)
        h2 = lock_hash(doc)
        assert h1 == h2

    def test_different_docs_differ(self) -> None:
        d1 = build_lock_doc("scent_model", "v1", {}, {})
        d2 = build_lock_doc("scent_model", "v2", {}, {})
        assert lock_hash(d1) != lock_hash(d2)

    def test_rejects_wrong_keys(self) -> None:
        with pytest.raises(ValueError, match="lock doc must have exactly"):
            lock_hash({"family": "scent_model", "name": "v1"})  # missing keys

    def test_rejects_extra_keys(self) -> None:
        with pytest.raises(ValueError, match="lock doc must have exactly"):
            lock_hash({
                "family": "scent_model",
                "name": "v1",
                "params": {},
                "example": {},
                "extra": 1,
            })


class TestBuildLockDoc:
    """Tests for build_lock_doc — creates a valid four-key envelope."""

    def test_returns_dict_with_four_keys(self) -> None:
        doc = build_lock_doc("info_mode", "belief", {"mode": "belief"}, {})
        assert set(doc.keys()) == set(LOCK_DOC_KEYS)
        assert doc["family"] == "info_mode"
        assert doc["name"] == "belief"

    def test_rejects_unknown_family(self) -> None:
        with pytest.raises(ValueError, match="unknown family"):
            build_lock_doc("unknown_family", "v1", {}, {})

    def test_all_families_accepted(self) -> None:
        for family in LOCK_FAMILIES:
            doc = build_lock_doc(family, "v1", {}, {})
            assert doc["family"] == family
