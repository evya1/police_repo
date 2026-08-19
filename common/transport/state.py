"""The mandatory per-peer state machine (spec §8.3, Appendix E rules 4-5).

The official specification fixes one legal ordering for a peer's turn: it waits for
the opponent, computes a move, commits it, awaits the reveal, verifies, and returns to
waiting — the commit-then-reveal cycle of Appendix E rule 4. Rule 5 adds a single
absorbing terminal, ``TECHNICAL_LOSS``, reachable from any live state: a sub-game that
reaches it is lost, but the *series* is not, so the machine records the loss and stops
rather than letting a peer quietly abandon the remaining sub-games.

This module is a small, self-contained guard over that ordering. It is derived directly
from the specification's transition rules — it defines the legal edges once, refuses any
edge not on the map, and exposes the visited history as the replay hook (D7). It holds no
game, wire, or strategy logic; those belong to the drivers that thread it.
"""

from __future__ import annotations

from enum import StrEnum


class PeerState(StrEnum):
    """The six states of Appendix E rule 4, plus the rule-5 absorbing terminal."""

    WAITING_FOR_OPPONENT = "WAITING_FOR_OPPONENT"
    COMPUTING_MOVE = "COMPUTING_MOVE"
    COMMITTING = "COMMITTING"
    AWAITING_REVEAL = "AWAITING_REVEAL"
    VERIFYING = "VERIFYING"
    TECHNICAL_LOSS = "TECHNICAL_LOSS"


# The legal edges. Each live state may advance to exactly its successor in the
# commit-reveal cycle, or fall to the absorbing terminal; the terminal has no exits.
_CYCLE = (
    PeerState.WAITING_FOR_OPPONENT,
    PeerState.COMPUTING_MOVE,
    PeerState.COMMITTING,
    PeerState.AWAITING_REVEAL,
    PeerState.VERIFYING,
)
TRANSITIONS: dict[PeerState, frozenset[PeerState]] = {
    state: frozenset({_CYCLE[(i + 1) % len(_CYCLE)], PeerState.TECHNICAL_LOSS})
    for i, state in enumerate(_CYCLE)
}
TRANSITIONS[PeerState.TECHNICAL_LOSS] = frozenset()


class IllegalTransition(Exception):  # noqa: N818 — a transition, not an *Error condition
    """Raised when a caller asks for an edge the specification does not permit."""


class PeerStateMachine:
    """Guards one peer's turn ordering; records every state it passes through."""

    def __init__(self, start: PeerState = PeerState.WAITING_FOR_OPPONENT) -> None:
        self.state = start
        self.history: list[PeerState] = [start]

    def to(self, target: PeerState) -> PeerState:
        """Advance to ``target`` if the edge is legal, else raise ``IllegalTransition``."""
        if target not in TRANSITIONS[self.state]:
            legal = sorted(s.value for s in TRANSITIONS[self.state])
            raise IllegalTransition(
                f"{self.state.value} -> {target.value} is not a legal transition; "
                f"legal from here: {legal}")
        self.state = target
        self.history.append(target)
        return target

    def fail(self) -> None:
        """Fall to the absorbing terminal from anywhere — always legal, never reversible."""
        if self.state is not PeerState.TECHNICAL_LOSS:
            self.state = PeerState.TECHNICAL_LOSS
            self.history.append(self.state)

    @property
    def finished(self) -> bool:
        """True once the machine has reached the absorbing terminal."""
        return self.state is PeerState.TECHNICAL_LOSS
