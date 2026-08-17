"""Game ID and UID derivation.

Game IDs are sorted-pair strings (order-independent). UIDs are 16-byte UUID hex digests
derived from game_id concatenated with the terms hash. The terms signature commits both
the shared and private sides of the projection table.
"""

from __future__ import annotations

import hashlib
import json
import uuid


def game_id(role_a: str, role_b: str) -> str:
    """Return a sorted-pair game ID from the two role names.

    The pair is sorted so ``game_id('A', 'B') == game_id('B', 'A')`` — the ID is
    order-independent, which is what both peers need to agree on.
    """
    pair = sorted([role_a, role_b])
    return "-".join(pair)


def game_uid(game_id: str, terms_hash: str) -> str:
    """Return a 16-byte UUID hex derived from game_id + terms hash.

    The first 16 bytes of SHA-256(game_id|terms_hash) become a UUID hex string.
    This is the opaque handle used in artifacts and ledger rows.
    """
    combined = f"{game_id}|{terms_hash}".encode()
    digest = hashlib.sha256(combined).digest()
    return uuid.UUID(bytes=digest[:16]).hex


def terms_signature(shared: dict, private: dict) -> str:
    """Return a SHA-256 signature over projected shared + private terms.

    The combined dict is canonicalized (sorted keys, compact separators, no ASCII escape)
    so both peers arrive at the same hash even if their dict insertion order differs.
    """
    combined = json.dumps(
        {"shared": shared, "private": private},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()
