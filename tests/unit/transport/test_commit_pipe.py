"""Targeted regression test: ``common.transport.canonical.commit`` uses the pipe separator.

Ensures the commit-reveal construction matches the reference protocol
(SPEC section 3 of references/copthief-league-protocol):

    commit = SHA256( canonical_json(payload) + "|" + nonce )

Regresses the bug where the ``|`` separator was dropped in ``canonical.commit``,
causing every audit to fail against any reference-protocol peer (FR-29: both
sides zeroed). See ``notes/commit-pipe-bug/REPORT.md`` for the full evidence trail.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from common.transport.canonical import commit, verify_commit
from common.transport.ids import terms_signature

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def reference_commit(payload: dict, nonce: str) -> str:
    """SPEC section 3 construction, inlined so this test has no external deps.

    ``SHA256(canonical_json(payload) + "|" + nonce)`` with the agreed
    canonicalization (sorted keys, compact separators, literal non-ASCII).
    """
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(f"{canonical}|{nonce}".encode()).hexdigest()


# Externally sourced anchors: two vectors published by the kit itself
# (references/copthief-league-protocol/vectors/commit_reveal.json, status CORE).
# The second pins ensure_ascii=False — a Unicode implementation drift would
# fail it even with the pipe in place.
KIT_PUBLISHED_VECTORS = [
    {
        "payload": {
            "step": 0,
            "type": "system_spec",
            "spec": {"os": "Linux", "cpu_cores": 4, "ram_gb": 16.0, "vram_gb": 0.0},
            "model": "cli-default",
            "code_version": "1.0",
            "group_name": "Example-Team",
            "sub_game_number": 1,
        },
        "nonce": "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
        "commit": "69c9a786d18829990291cd0ffb768eacfa009011b0c89a6f4f32330551e2003e",
    },
    {
        "payload": {
            "step": 2,
            "state": "grid=7x7;self=[2, 4];barriers=[[1, 1]]",
            "position": [2, 4],
            "move": "MOVE:N",
            "intent": "lie",
            "hint": "אני ליד הכיכר 🙂",
        },
        "nonce": "deadbeefcafef00dfeedface00c0ffee",
        "commit": "2caaeb0a7e656868b85166a9ebe34226bae4fdcb79cb7a0a23759121769d9338",
    },
]


class TestCommitMatchesReferenceConstruction:
    """The bug under test: canonical.commit must equal the pipe construction."""

    @pytest.mark.parametrize(
        ("payload", "nonce"),
        [
            ({"move": "N", "step": 1}, "deadbeefcafe1234"),
            (
                {
                    "step": 1,
                    "sender": "thief",
                    "intent": "evade",
                    "move": "MOVE:N",
                    "hint": "I keep to the main avenues.",
                    "state": "grid=7x7;self=[4, 3];barriers=[]",
                },
                "112233445566778899aabbccddeeff00",
            ),
            ({"value": 0.1, "hint": "אני ליד הכיכר 🙂"}, "nonce-unicode-float"),
        ],
        ids=["ascii", "turn-record", "unicode-float"],
    )
    def test_commit_equals_pipe_construction(self, payload: dict, nonce: str) -> None:
        ours = commit(payload, nonce)
        reference = reference_commit(payload, nonce)
        assert ours == reference, (
            "commit() does not match the reference construction (SPEC §3: "
            f"SHA256(canonical + '|' + nonce)).\n"
            f"  ours      = {ours}\n"
            f"  reference = {reference}\n"
            "Root cause: the '|' separator is dropped in canonical.commit."
        )

    @pytest.mark.parametrize("vector", KIT_PUBLISHED_VECTORS, ids=["step-0-spec", "unicode-hint"])
    def test_reproduces_kit_published_core_vector(self, vector: dict) -> None:
        assert commit(vector["payload"], vector["nonce"]) == vector["commit"], (
            "our commit does not reproduce a CORE vector published by the kit; "
            "any reference-protocol peer will re-hash our audit differently and "
            "verdict TAMPERED (both sides zeroed, FR-29)."
        )


class TestVendoredFixtureConsistency:
    """The pinned fixtures must pin the CONSTRUCTION, not the implementation.

    These fail today because the fixtures were generated from the buggy
    function; they pass after the fix plus fixture regeneration.
    """

    @pytest.mark.parametrize("name", ["commit_reveal.json", "turn_message.json"])
    def test_vendored_fixture_pins_the_reference_construction(self, name: str) -> None:
        with open(ROOT / "tests" / "contract" / "vectors" / name, encoding="utf-8") as f:
            vec = json.load(f)
        if name == "commit_reveal.json":
            payload, nonce, pinned = vec["payload"], vec["nonce"], vec["commit"]
        else:  # turn_message.json — the full message (including nonce field) is the payload
            pinned = vec["commit"]
            nonce = vec["message"]["nonce"]
            payload = vec["message"]
        assert pinned == reference_commit(payload, nonce), (
            f"{name} pins a commit that the reference construction cannot "
            f"reproduce (pinned {pinned[:16]}... vs {reference_commit(payload, nonce)[:16]}...). "
            "The fixture was generated from the buggy implementation — regenerate it."
        )


class TestContrastHandshakeIsCorrect:
    """ids.terms_signature already uses the pipe form (the match starts fine;

    only step commits break). Locked in so a future 'simplification' cannot
    silently re-break the handshake.
    """

    def test_terms_signature_matches_reference(self) -> None:
        terms = {"board_size": 7, "num_games": 6, "setting": "Haifa"}
        nonce = "a1a2a3a4b1b2b3b4c1c2c3c4d1d2d3d4"
        assert terms_signature(terms, nonce) == reference_commit(terms, nonce)


class TestVerifyCommitConsistency:
    """verify_commit must agree with the reference form once commit is fixed."""

    def test_verify_accepts_reference_form(self) -> None:
        payload, nonce = {"move": "N", "step": 1}, "deadbeefcafe1234"
        assert verify_commit(payload, nonce, reference_commit(payload, nonce)) is True
