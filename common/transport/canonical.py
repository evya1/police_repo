"""Byte-level canonicalization: the single SHA-256 path.

Canonical JSON (RFC 8785 style) — sorted keys, compact separators, no ASCII escaping — is the
only hash path the league permits. Every commit, every terms signature, every UID derives from
this one function, so a drift in serialization is caught before it leaks into a result.
"""

from __future__ import annotations

import hashlib
import json


def canonical_bytes(data: dict) -> bytes:
    """Return canonical JSON bytes for the given dict.

    Uses sorted keys, compact separators, and ensure_ascii=False per RFC 8785.
    Unicode is preserved, not escaped to ``\\uXXXX``.
    """
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def commit(payload: dict, nonce: str) -> str:
    """Return a SHA-256 commit over canonical(payload) concatenated with nonce.

    The nonce is pipe-appended (concatenated, not structurally embedded) so the
    receiver can verify by re-canonicalizing and re-hashing.
    """
    payload_bytes = canonical_bytes(payload)
    combined = payload_bytes + nonce.encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def verify_commit(payload: dict, nonce: str, expected: str) -> bool:
    """Return True when ``commit(payload, nonce)`` matches ``expected``."""
    return commit(payload, nonce) == expected
