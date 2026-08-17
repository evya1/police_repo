"""Game ID and UID derivation.

Game IDs are sorted-pair strings with ``-vs-`` between them (order-independent).
UIDs are 16-byte UUID hex digests derived from ``SHA256(canonical(terms) + "|" +
"|".join(sorted(group_ids)))[:16]``. The exact derivation matches the kit's
``ref_game_uid`` / ``ref_game_id`` so golden vectors reproduce byte-for-byte.
"""

from __future__ import annotations

import hashlib
import uuid

from common.transport.canonical import canonical_bytes


def game_id(role_a: str, role_b: str) -> str:
    """Return a sorted-pair game ID from the two role names.

    Uses ``-vs-`` between the sorted pair so it matches the kit's
    ``ref_game_id`` exactly. The pair is sorted so
    ``game_id('A', 'B') == game_id('B', 'A')`` — the ID is order-independent,
    which is what both peers need to agree on.
    """
    return "-vs-".join(sorted([role_a, role_b]))


def game_uid(terms: dict, group_a: str, group_b: str) -> str:
    """Return a 16-byte UUID hex derived from terms + sorted group ids.

    Matches the kit's ``ref_game_uid``:
    ``UUID(SHA256(canonical(terms) + "|" + "|".join(sorted([a, b])))[:16])``.
    Both peers derive the same value with no round-trip because the terms
    already value-equal at the point this is called.
    """
    pair = sorted([group_a, group_b])
    seed = f"{canonical_bytes(terms).decode('utf-8')}|{'|'.join(pair)}"
    return str(uuid.UUID(bytes=hashlib.sha256(seed.encode("utf-8")).digest()[:16]))


def terms_signature(terms: dict, nonce: str) -> str:
    """Return a SHA-256 signature over canonical(terms) with the nonce pipe-appended.

    Matches the kit's ``ref_terms_signature`` / ``ref_commit``:
    ``SHA256(canonical_json(terms) + "|" + nonce)``.
    """
    return hashlib.sha256(
        f"{canonical_bytes(terms).decode('utf-8')}|{nonce}".encode()
    ).hexdigest()
