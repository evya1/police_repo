"""Lock families and lock decision logic.

STUB — to be replaced by the real implementation in ST-06 (T009).
"""

from __future__ import annotations

# Known lock families — extended as the league defines more.
LOCK_FAMILIES: frozenset[str] = frozenset({
    "reference-v3",
})


def lock_decision(declared_family: str | None, our_family: str) -> str:
    """Return 'accept', 'refuse', or 'silence' for a lock declaration.

    STUB: accept-all placeholder.
    The real implementation will enforce the pinned doc + hash and refuse
    when both peers declare a family and disagree (FR-14/FR-16).
    """
    if declared_family is None:
        return "silence"
    if declared_family == our_family:
        return "accept"
    return "refuse"


def lock_hash(family: str) -> str:
    """Return the pinned hash for a lock family.

    STUB: placeholder.
    """
    import hashlib

    return hashlib.sha256(family.encode("utf-8")).hexdigest()
