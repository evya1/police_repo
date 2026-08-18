"""Integrity primitives: nonce generation, commit/reveal, and audit records.

Nonces are 16-byte hex strings from ``secrets.token_hex`` (cryptographically secure).
Audit records carry the state, the move, the intent label, and the nonce that binds them.
"""

from __future__ import annotations

import secrets


def new_nonce() -> str:
    """Return a fresh 32-char hex nonce (16 bytes)."""
    return secrets.token_hex(16)


def audit_payload(state: str, move: str, intent: str, nonce: str) -> dict:
    """Build a step-0 / turn audit record.

    The nonce binds the state+move+intent triple so the receiver can verify it was not
    retrofitted after the fact. The nonce must remain secret until the audit phase.
    """
    return {
        "state": state,
        "move": move,
        "intent": intent,
        "nonce": nonce,
    }
