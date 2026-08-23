"""Contract test: canonical JSON / signature / UID construction against the pinned
`copthief-league-protocol` kit's OWN vectors, read directly from the pinned external
checkout (not a vendored copy) -- the live oracle for `kit_interop` conformance (T052,
ADR-011). Pinned commit ad6557626587e09146af4283a5e808e7001343c5, MIT licensed,
https://github.com/Imreec/copthief-league-protocol.

Also proves the required non-ASCII (Hebrew + emoji) case: `ensure_ascii=False` is
exercised, not merely asserted, by round-tripping raw non-ASCII bytes through the exact
construction the kit's SPEC section 4 pins.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.transport.canonical import canonical_bytes, commit, verify_commit
from common.transport.ids import game_id, game_uid, terms_signature

KIT_ROOT = Path("/home/user/imreec/copthief-league-protocol")
KIT_VECTORS = KIT_ROOT / "vectors"

pytestmark = pytest.mark.skipif(
    not KIT_VECTORS.is_dir(),
    reason="pinned external kit checkout not available in this environment",
)


def _load(name: str) -> dict:
    with open(KIT_VECTORS / name, encoding="utf-8") as f:
        return json.load(f)


class TestKitTermsSignature:
    """SPEC 4: signature = SHA256(canonical_json(terms)|nonce), single '|' separator."""

    def test_kit_vector_reproduced_byte_for_byte(self) -> None:
        for vec in _load("terms_signature.json")["vectors"]:
            computed = terms_signature(vec["terms"], vec["nonce"])
            assert computed == vec["signature"]


class TestKitGameUidAndGameId:
    """SPEC 4: game_uid/game_id both sort the pair -- order-independent for both peers."""

    def test_kit_vectors_reproduced_byte_for_byte(self) -> None:
        for vec in _load("game_uid.json")["vectors"]:
            uid = game_uid(vec["terms"], vec["group_a"], vec["group_b"])
            gid = game_id(vec["group_a"], vec["group_b"])
            assert uid == vec["game_uid"]
            assert gid == vec["game_id"]

    def test_swapped_groups_are_order_independent(self) -> None:
        vecs = _load("game_uid.json")["vectors"]
        assert len(vecs) >= 2
        first, second = vecs[0], vecs[1]
        assert first["game_uid"] == second["game_uid"]
        assert first["game_id"] == second["game_id"]


class TestKitCommitReveal:
    """SPEC 3/4: the same construction used for turn commits, over the kit's own vector."""

    def test_kit_vector_reproduced_byte_for_byte(self) -> None:
        vec = _load("commit_reveal.json")
        cases = vec.get("vectors", [vec])
        for case in cases:
            computed = commit(case["payload"], case["nonce"])
            assert computed == case["commit"]
            assert verify_commit(case["payload"], case["nonce"], case["commit"]) is True


class TestKitCanonicalJson:
    """SPEC 2/4: sorted keys, compact separators, ensure_ascii=False -- against the kit's own
    canonical_json.json vector set, not just this repo's local copy."""

    def test_kit_vector_cases_reproduced(self) -> None:
        import hashlib

        vec = _load("canonical_json.json")
        cases = vec["vectors"]
        assert cases, "expected a case list in the kit's canonical_json.json"
        for case in cases:
            produced = canonical_bytes(case["object"])
            assert produced == case["canonical"].encode("utf-8")
            if "sha256" in case:
                assert hashlib.sha256(produced).hexdigest() == case["sha256"]


def test_hebrew_and_emoji_ensure_ascii_false_not_just_asserted() -> None:
    """A regression to `ensure_ascii=True` would still pass every English-only vector above
    (SPEC 4's own warning) -- this is the case that catches it."""
    terms = {"setting": "חיפה", "note": "🎲 בדיקה"}
    nonce = "hebrew-emoji-nonce"

    raw = canonical_bytes(terms)
    assert "\\u" not in raw.decode("utf-8")
    assert "חיפה" in raw.decode("utf-8") and "🎲" in raw.decode("utf-8")

    sig = terms_signature(terms, nonce)
    expected = json.dumps(terms, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    import hashlib

    assert sig == hashlib.sha256(f"{expected}|{nonce}".encode()).hexdigest()

    # And the single-'|' commit construction, over the same non-ASCII payload.
    payload = {"step": 1, "sender": "thief", "hint": terms["note"]}
    c = commit(payload, nonce)
    assert verify_commit(payload, nonce, c) is True
    assert not verify_commit(payload, nonce + "x", c)
