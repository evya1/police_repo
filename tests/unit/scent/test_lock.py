"""Model lock tests.

Covers T005 L82, L87:
* both published sha256 values reproduced
* same input → same hash (determinism)
* full 5-row refusal truth table
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from police_peer.scent import PINNED_DOCS, canonical_json, model_lock_hash, refusal_decision

FIXTURE = Path(__file__).parent / "fixtures" / "locked_model.json"


@pytest.fixture()
def fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestPublishedHashes:
    """Both published sha256 values reproduced from the pinned docs."""

    def test_subtractive_hash(self) -> None:
        expected = "81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4"
        result = model_lock_hash("subtractive_chebyshev_v1")
        assert result == expected

    def test_book_hash(self) -> None:
        expected = "934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9"
        result = model_lock_hash("multiplicative_book_v1")
        assert result == expected

    def test_hashes_match_fixture(self, fixture: dict) -> None:
        """Cross-check against the published values in locked_model.json."""
        registered = fixture["registered"]
        subtractive_doc = next(
            r for r in registered if r["doc"]["name"] == "subtractive_chebyshev_v1"
        )
        book_doc = next(
            r for r in registered if r["doc"]["name"] == "multiplicative_book_v1"
        )
        assert model_lock_hash("subtractive_chebyshev_v1") == subtractive_doc["sha256"]
        assert model_lock_hash("multiplicative_book_v1") == book_doc["sha256"]


class TestDeterminism:
    """Same input → same hash."""

    def test_canonical_json_deterministic(self) -> None:
        obj = {"z": 1, "a": [3, 2, 1]}
        first = canonical_json(obj)
        second = canonical_json(obj)
        assert first == second

    def test_hash_deterministic(self) -> None:
        h1 = model_lock_hash("subtractive_chebyshev_v1")
        h2 = model_lock_hash("subtractive_chebyshev_v1")
        assert h1 == h2

    def test_canonical_json_sorts_keys(self) -> None:
        obj = {"b": 2, "a": 1}
        result = canonical_json(obj)
        # Keys must be sorted
        assert result == '{"a":1,"b":2}'

    def test_canonical_json_compact(self) -> None:
        obj = {"a": [1, 2]}
        result = canonical_json(obj)
        # No spaces after separators
        assert result == '{"a":[1,2]}'

    def test_canonical_json_no_ascii_escape(self) -> None:
        obj = {"emoji": "😀"}
        result = canonical_json(obj)
        assert "😀" in result


class TestRefusalTruthTable:
    """Full 5-row refusal truth table from locked_model.json L397–428."""

    SUB = "81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4"
    BOOK = "934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9"

    def test_both_same_play(self) -> None:
        assert refusal_decision(self.SUB, self.SUB) == "play"

    def test_both_different_refuse(self) -> None:
        assert refusal_decision(self.SUB, self.BOOK) == "refuse"

    def test_ours_declares_theirs_silent_play(self) -> None:
        assert refusal_decision(self.SUB, None) == "play"

    def test_ours_silent_theirs_declares_play(self) -> None:
        assert refusal_decision(None, self.BOOK) == "play"

    def test_neither_declares_play(self) -> None:
        assert refusal_decision(None, None) == "play"

    def test_truth_table_matches_fixture(self, fixture: dict) -> None:
        """Verify the refusal_decision logic matches the fixture's truth table."""
        for row in fixture["refusal_rule"]:
            ours = row["ours"]
            theirs = row["theirs"]
            expected = row["decision"]
            assert refusal_decision(ours, theirs) == expected


class TestPinnedDocs:
    """PINNED_DOCS contains both registered scent model documents."""

    def test_both_models_present(self) -> None:
        assert "subtractive_chebyshev_v1" in PINNED_DOCS
        assert "multiplicative_book_v1" in PINNED_DOCS

    def test_subtractive_doc_structure(self) -> None:
        doc = PINNED_DOCS["subtractive_chebyshev_v1"]
        assert doc["family"] == "scent_model"
        assert doc["name"] == "subtractive_chebyshev_v1"
        assert doc["params"]["field_size"] == 5
        assert doc["params"]["emit_intensity"] == 0.9
        assert doc["params"]["decay_per_step"] == 0.1

    def test_book_doc_structure(self) -> None:
        doc = PINNED_DOCS["multiplicative_book_v1"]
        assert doc["family"] == "scent_model"
        assert doc["name"] == "multiplicative_book_v1"
        assert doc["params"]["field_size"] == 5
        assert doc["params"]["center_intensity"] == 0.9
        assert doc["params"]["decay_rho"] == 0.1
        assert len(doc["params"]["kernel"]) == 5


class TestNoForgedScentLock:
    """T005 L86: refusal fires at handshake boundary, never inside the scent module.

    The refusal_decision function is pure and unit-testable without a wire.
    The actual refusal fires at the handshake boundary (C03), which is out of scope.
    """

    SUB = "81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4"
    BOOK = "934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9"

    def test_refusal_is_pure_function(self) -> None:
        """refusal_decision takes hashes, returns a decision — no I/O."""
        result = refusal_decision(self.SUB, self.BOOK)
        assert result == "refuse"
        assert isinstance(result, str)
