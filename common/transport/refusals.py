"""Refusal codes and diagnostics.

STUB — to be replaced by the real implementation in ST-06 (T009).
"""

from __future__ import annotations

# SPAR-N00…N10 refusal codes.
REFUSAL_CODES = frozenset({
    "SPAR-N00",
    "SPAR-N01",
    "SPAR-N02",
    "SPAR-N03",
    "SPAR-N04",
    "SPAR-N05",
    "SPAR-N06",
    "SPAR-N07",
    "SPAR-N08",
    "SPAR-N09",
    "SPAR-N10",
})


def refuse(code: str, detail: str = "") -> dict:
    """Build a refusal message to send via receive_control.

    STUB: placeholder.
    """
    return {
        "kind": "refusal",
        "code": code,
        "detail": detail,
    }


def is_refusal(code: str) -> bool:
    """Return True when `code` is a known refusal code."""
    return code in REFUSAL_CODES
