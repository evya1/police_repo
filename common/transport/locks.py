"""Lock families and lock decision logic.

The refusal rule is simple but deliberate (SPEC section 7): refuse only when
both peers declare a family and the hashes disagree. Omission on either side
is never refusal — the unmodified reference peer declares nothing at all, and
a guard that fail-fasts on silence forfeits that game to itself.

Four families ride the negotiate wire as ``<family>_sha256`` — a compact
SHA-256 over a pinned four-key document (``family``, ``name``, ``params``,
``example``). The document itself never crosses the wire; only the hash does.
"""

from __future__ import annotations

import hashlib

from common.transport.canonical import canonical_bytes

#: The four known lock families. Extended as the league defines more.
LOCK_FAMILIES: frozenset[str] = frozenset({
    "scent_model",
    "wire_shape",
    "info_mode",
    "smell_binding",
})

#: The four keys a lock document must carry, in canonical order.
LOCK_DOC_KEYS: tuple[str, ...] = ("example", "family", "name", "params")


def lock_decision(our_hash: str | None, their_hash: str | None) -> str:
    """Return ``'accept'``, ``'refuse'``, or ``'silence'`` for a lock declaration.

    Refuse only when both peers declare a family and the hashes disagree.
    Omission (``None``) on either side is silence, not refusal.
    """
    if our_hash is None or their_hash is None:
        return "silence"
    if our_hash == their_hash:
        return "accept"
    return "refuse"


def lock_hash(doc: dict) -> str:
    """Return the SHA-256 hash of a lock document.

    The document must carry exactly the four canonical keys
    (``example``, ``family``, ``name``, ``params``). The hash is over the
    compact canonical JSON (sorted keys, no ASCII escaping, no spaces).
    """
    if tuple(sorted(doc)) != LOCK_DOC_KEYS:
        raise ValueError(
            f"lock doc must have exactly {LOCK_DOC_KEYS}, got {tuple(sorted(doc))}"
        )
    return hashlib.sha256(canonical_bytes(doc)).hexdigest()


def build_lock_doc(family: str, name: str, params: dict, example: dict) -> dict:
    """Build a locked-model document for hashing.

    ``family`` must be one of :data:`LOCK_FAMILIES`. The document is the
    four-key envelope that gets hashed and declared as ``<family>_sha256``.
    """
    if family not in LOCK_FAMILIES:
        raise ValueError(
            f"unknown family {family!r}; expected one of {LOCK_FAMILIES}"
        )
    return {
        "family": family,
        "name": name,
        "params": params,
        "example": example,
    }
