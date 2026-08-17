"""Golden-vector contract tests: reproduce every vendored fixture byte-for-byte.

TC-25, T008 `{#early_byte_vectors}` — run here, not deferred to T022.
Each JSON file in ``tests/contract/vectors/`` is a fixed expectation. The test
re-computes the value from the current implementation and asserts equality.

Provenance (upstream SHA per EVID-003; non-authoritative, PRD C1):
  canonical_json.json   — RFC 8785 style canonical JSON vectors
  commit_reveal.json    — pipe-appended nonce commit/reveal vector
  terms_signature.json  — shared+private terms signature vector
  game_uid.json         — sorted-pair game ID → 16-byte UUID vector
  delivery_contract.json — contract canonicalization vector
  locked_model.json     — locked model canonicalization vector
  pairing_declaration.json — sorted game_id pairing vector
  turn_message.json     — turn message canonicalization + commit vector
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from common.transport.canonical import canonical_bytes, commit, verify_commit
from common.transport.ids import game_id, game_uid, terms_signature

VECTORS_DIR = Path(__file__).resolve().parents[1] / "contract" / "vectors"


class TestCanonicalJson:
    """TC-25: canonical JSON vectors reproduced byte-for-byte."""

    def _load(self) -> dict:
        with open(VECTORS_DIR / "canonical_json.json", encoding="utf-8") as f:
            return json.load(f)

    def test_empty(self) -> None:
        vec = self._load()
        assert canonical_bytes({}) == vec["empty"].encode("utf-8")

    def test_single_key(self) -> None:
        vec = self._load()
        assert canonical_bytes({"a": 1}) == vec["single_key"].encode("utf-8")

    def test_multiple_keys_sorted(self) -> None:
        vec = self._load()
        assert canonical_bytes({"z": 1, "a": 2, "m": 3}) == vec["multiple_keys_sorted"].encode(
            "utf-8"
        )

    def test_nested_dict_sorted(self) -> None:
        vec = self._load()
        assert canonical_bytes({"b": {"y": 2, "x": 1}, "a": 3}) == vec["nested_sorted"].encode(
            "utf-8"
        )

    def test_unicode_preserved(self) -> None:
        vec = self._load()
        result = canonical_bytes({"name": "שלום", "emoji": "🎲"})
        assert result == vec["unicode"].encode("utf-8")
        assert b"\\u" not in result

    def test_float_repr(self) -> None:
        vec = self._load()
        assert canonical_bytes({"value": 1.5}) == vec["float"].encode("utf-8")

    def test_bool_preserved(self) -> None:
        vec = self._load()
        assert canonical_bytes({"flag": True, "other": False}) == vec["bool"].encode("utf-8")

    def test_null_preserved(self) -> None:
        vec = self._load()
        assert canonical_bytes({"x": None}) == vec["null"].encode("utf-8")

    def test_array_preserved(self) -> None:
        vec = self._load()
        assert canonical_bytes({"items": [1, 2, 3]}) == vec["array"].encode("utf-8")


class TestCommitReveal:
    """TC-25: commit/reveal vector reproduced byte-for-byte."""

    def test_reproduce(self) -> None:
        with open(VECTORS_DIR / "commit_reveal.json", encoding="utf-8") as f:
            vec = json.load(f)
        computed = commit(vec["payload"], vec["nonce"])
        assert computed == vec["commit"]
        assert verify_commit(vec["payload"], vec["nonce"], vec["commit"]) is True


class TestTermsSignature:
    """TC-25: terms signature vector reproduced byte-for-byte."""

    def test_reproduce(self) -> None:
        with open(VECTORS_DIR / "terms_signature.json", encoding="utf-8") as f:
            vec = json.load(f)
        # The fixture now carries the combined terms and nonce.
        terms = {"shared": vec["shared"], "private": vec["private"]}
        computed = terms_signature(terms, vec["nonce"])
        assert computed == vec["signature"]
        # Canonical form must also match
        expected_canonical = json.dumps(
            terms,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        assert canonical_bytes(terms) == vec["canonical"].encode("utf-8")
        assert expected_canonical == vec["canonical"].encode("utf-8")


class TestGameUid:
    """TC-25: game UID vector reproduced byte-for-byte."""

    def test_reproduce(self) -> None:
        with open(VECTORS_DIR / "game_uid.json", encoding="utf-8") as f:
            vec = json.load(f)
        computed = game_uid(vec["terms"], vec["group_a"], vec["group_b"])
        assert computed == vec["uid"]
        # Also verify via the raw derivation.
        from common.transport.canonical import canonical_bytes
        terms_bytes = canonical_bytes(vec["terms"])
        pair = sorted([vec["group_a"], vec["group_b"]])
        seed = f"{terms_bytes.decode('utf-8')}|{'|'.join(pair)}"
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        expected = str(uuid.UUID(bytes=digest[:16]))
        assert computed == expected


class TestDeliveryContract:
    """TC-25: delivery contract canonicalization vector reproduced byte-for-byte."""

    def test_reproduce(self) -> None:
        with open(VECTORS_DIR / "delivery_contract.json", encoding="utf-8") as f:
            vec = json.load(f)
        contract = vec["contract"]
        computed_bytes = canonical_bytes(contract)
        assert computed_bytes == vec["canonical_bytes"].encode("utf-8")
        computed_hash = hashlib.sha256(computed_bytes).hexdigest()
        assert computed_hash == vec["canonical_sha256"]


class TestLockedModel:
    """TC-25: locked model canonicalization vector reproduced byte-for-byte."""

    def test_reproduce(self) -> None:
        with open(VECTORS_DIR / "locked_model.json", encoding="utf-8") as f:
            vec = json.load(f)
        model = vec["model"]
        computed_bytes = canonical_bytes(model)
        assert computed_bytes == vec["canonical_bytes"].encode("utf-8")
        computed_hash = hashlib.sha256(computed_bytes).hexdigest()
        assert computed_hash == vec["canonical_sha256"]


class TestPairingDeclaration:
    """TC-25: pairing declaration — sorted game_id correctness."""

    def test_sorted_game_id(self) -> None:
        with open(VECTORS_DIR / "pairing_declaration.json", encoding="utf-8") as f:
            vec = json.load(f)
        declaration = vec["declaration"]
        computed = game_id(declaration["role_a"], declaration["role_b"])
        assert computed == vec["sorted_game_id"]
        # Symmetry: order must not matter
        assert game_id(declaration["role_b"], declaration["role_a"]) == vec["sorted_game_id"]
        # The -vs- separator is the canonical form (matches ref_game_id).
        assert "-vs-" in computed


class TestTurnMessage:
    """TC-25: turn message canonicalization + commit vector reproduced byte-for-byte."""

    def test_reproduce(self) -> None:
        with open(VECTORS_DIR / "turn_message.json", encoding="utf-8") as f:
            vec = json.load(f)
        message = vec["message"]
        computed_bytes = canonical_bytes(message)
        assert computed_bytes == vec["canonical_bytes"].encode("utf-8")
        computed_hash = hashlib.sha256(computed_bytes).hexdigest()
        assert computed_hash == vec["canonical_sha256"]
        # Commit must match
        computed_commit = commit(message, vec["message"]["nonce"])
        assert computed_commit == vec["commit"]
