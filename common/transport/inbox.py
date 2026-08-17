"""At-least-once inbox with duplicate absorption and bounded reordering.

STUB — to be replaced by the real implementation in ST-08 (T012).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class DeliveryDecision:
    """Return code from `delivery_decision`."""

    ABSORB = "absorb"
    EQUIVOCATION_LOUD = "equivocation_loud"
    BUFFER = "buffer"
    APPLY_DRAIN = "apply_drain"
    DISCARD = "discard"
    VIOLATION = "violation"


class DeadlineDecision:
    """Return code from `deadline_decision`."""

    OK = "ok"
    EXPIRED = "expired"
    RENEWED = "renewed"


@dataclass
class InboxState:
    """Per-sub-game inbox state."""

    received_commits: dict[int, str] = field(default_factory=dict)
    applied_steps: list[int] = field(default_factory=list)
    window_start: int = 0
    window: int = 4  # configurable, default 4, never 0


class Inbox:
    """Absorb/duplicate-absorb/buffer/discard decisions for turn messages.

    STUB: minimal placeholder.
    The real implementation (ST-08) will enforce the six-way pinned table:
    duplicates keyed on commit (not kind+step), bounded window, loud
    equivocation, and deadline judgment every lap.
    """

    def __init__(self, window: int = 4) -> None:
        if window <= 0:
            raise ValueError(f"window must be > 0, got {window}")
        self._state = InboxState()
        self._window = window
        self._decisions: list[str] = []

    def offer(self, step: int, commit: str, message: dict) -> str:
        """Absorb or buffer a turn message. Return a DeliveryDecision code."""
        # STUB: always apply-drain placeholder
        self._decisions.append(DeliveryDecision.APPLY_DRAIN)
        self._state.received_commits[step] = commit
        self._state.applied_steps.append(step)
        return DeliveryDecision.APPLY_DRAIN

    def decision(self) -> list[str]:
        """Return the sequence of decisions made so far."""
        return list(self._decisions)

    def reset_for_subgame(self) -> None:
        """Clear state for the next sub-game."""
        self._state = InboxState()
        self._decisions.clear()


def delivery_decision(
    state: InboxState, step: int, commit: str, message: dict
) -> str:
    """Pure six-way decision function.

    STUB: placeholder.
    """
    if commit in state.received_commits:
        if state.received_commits[commit] == commit:
            return DeliveryDecision.ABSORB
        return DeliveryDecision.EQUIVOCATION_LOUD
    if step < state.window_start:
        return DeliveryDecision.DISCARD
    if step < state.window_start + state.window:
        return DeliveryDecision.BUFFER
    return DeliveryDecision.VIOLATION


def deadline_decision(state: InboxState, now: float, expiry: float) -> str:
    """Pure deadline judgment.

    STUB: placeholder.
    """
    if now > expiry:
        return DeadlineDecision.EXPIRED
    return DeadlineDecision.OK
