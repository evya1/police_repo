"""Shared transport layer for the distributed Police/Thief game.

This package holds the role-agnostic protocol layer: the channel abstraction,
the loopback transport for testing, and all message shapes used during
negotiation, turns, audits, and control signals.

Both peers import this package and must stay byte-identical across the
police_repo and thief_repo — the `common/` sync check (SC-6, TC-24) verifies
this at Stage 2.
"""

from __future__ import annotations

__all__ = [
    "Inboxes",
    "LoopbackPeer",
    "LoopbackTransport",
    "PeerChannel",
    "pair",
]
