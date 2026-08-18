"""The mandatory state machine (book ch.8, App. E rules 4-5).

Ported from the reference kit (copthief-league-protocol, sparring/state.py) as the shared guard
for the subgame drivers. ``TECHNICAL_LOSS`` is absorbing on purpose: a sub-game that reaches it
is over, but the series is not — a series is six sub-games, and abandoning the rest would leave
the opponent playing a match we had quietly quit.
"""

from __future__ import annotations

from enum import StrEnum


class PeerState(StrEnum):
    WAITING_FOR_OPPONENT = "WAITING_FOR_OPPONENT"
    COMPUTING_MOVE = "COMPUTING_MOVE"
    COMMITTING = "COMMITTING"
    AWAITING_REVEAL = "AWAITING_REVEAL"
    VERIFYING = "VERIFYING"
    TECHNICAL_LOSS = "TECHNICAL_LOSS"


TRANSITIONS: dict[PeerState, frozenset[PeerState]] = {
    PeerState.WAITING_FOR_OPPONENT: frozenset({PeerState.COMPUTING_MOVE,
                                               PeerState.TECHNICAL_LOSS}),
    PeerState.COMPUTING_MOVE: frozenset({PeerState.COMMITTING, PeerState.TECHNICAL_LOSS}),
    PeerState.COMMITTING: frozenset({PeerState.AWAITING_REVEAL, PeerState.TECHNICAL_LOSS}),
    PeerState.AWAITING_REVEAL: frozenset({PeerState.VERIFYING, PeerState.TECHNICAL_LOSS}),
    PeerState.VERIFYING: frozenset({PeerState.WAITING_FOR_OPPONENT, PeerState.TECHNICAL_LOSS}),
    PeerState.TECHNICAL_LOSS: frozenset(),
}


class IllegalTransition(Exception):  # noqa: N818 (kit verbatim)
    pass


class PeerStateMachine:
    def __init__(self, start: PeerState = PeerState.WAITING_FOR_OPPONENT) -> None:
        self.state = start
        self.history: list[PeerState] = [start]

    def to(self, target: PeerState) -> PeerState:
        if target not in TRANSITIONS[self.state]:
            raise IllegalTransition(
                f"{self.state.value} -> {target.value} is not a legal transition; "
                f"legal from here: {sorted(s.value for s in TRANSITIONS[self.state])}")
        self.state = target
        self.history.append(target)
        return target

    def fail(self) -> None:
        """Enter the absorbing terminal state from anywhere. Always legal; never reversible."""
        if self.state is not PeerState.TECHNICAL_LOSS:
            self.state = PeerState.TECHNICAL_LOSS
            self.history.append(self.state)

    @property
    def finished(self) -> bool:
        return self.state is PeerState.TECHNICAL_LOSS
