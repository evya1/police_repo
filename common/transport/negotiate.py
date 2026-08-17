"""Negotiation: greeting, verification, and refusal logic.

STUB — to be replaced by the real implementation in ST-06 (T009).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Greeting:
    """The signed negotiation message exchanged at handshake."""

    shared_terms: dict = field(default_factory=dict)
    private_terms: dict = field(default_factory=dict)
    lock_family: str | None = None
    game_id: str | None = None
    game_uid: str | None = None
    signature: str = ""
    # FR-20 omission convention: role is omitted (not None) when not declared.


def our_greeting(natural_role: str, terms: dict) -> Greeting:
    """Build our outgoing greeting.

    STUB: placeholder.
    """
    return Greeting(
        shared_terms=terms,
        lock_family="reference-v3",
    )


def verify_greeting(incoming: Greeting, our_terms: dict, our_role: str) -> tuple[bool, str]:
    """Verify an incoming greeting. Return (accepted, reason).

    STUB: accept-all placeholder.
    The real implementation will enforce the fixed FR-13 order:
    terms present → 14 keys → value-equality → signature re-verify → locks → pairing → uid.
    """
    return True, "accepted"


def classify_refusal(code: str) -> str:
    """Return a human-readable diagnostic for a refusal code.

    SPAR-N00…N10 codes.
    """
    diagnostics = {
        "SPAR-N00": "terms_missing: shared terms section absent",
        "SPAR-N01": "terms_keys_missing: one or more of the 14 required keys absent",
        "SPAR-N02": "terms_value_mismatch: key '{key}' differs",
        "SPAR-N03": "signature_drift: canonical strings differ",
        "SPAR-N04": "lock_disagree: both declared families differ",
        "SPAR-N05": "uid_missing: uid omitted in sub-game 1",
        "SPAR-N06": "uid_declared_early: uid declared before sub-game 1",
        "SPAR-N07": "uid_mismatch: declared uid differs from derived uid",
        "SPAR-N08": "both_declare_disagree: both sides declare conflicting families",
        "SPAR-N09": "arrived: opponent answered within handshake budget",
        "SPAR-N10": "turn_order_disagreement: thief expected to move first",
    }
    return diagnostics.get(code, f"unknown refusal code: {code}")
