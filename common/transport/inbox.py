"""At-least-once inbox with duplicate absorption and bounded reordering.

FR-32/FR-33: the receiver contract for an unordered, duplicating transport.
HTTP is at-least-once, so a retry produces an exact duplicate by design.
A receiver that treats the second copy as a violation converts a flaky
tunnel into a self-inflicted technical loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class DeliveryDecision:
    """Return codes from `delivery_decision`."""

    ABSORB = "absorb"
    EQUIVOCATION_LOUD = "equivocation_loud"
    BUFFER = "buffer"
    APPLY_DRAIN = "apply_drain"
    DISCARD = "discard"
    VIOLATION = "violation"


class DeadlineDecision:
    """Return codes from `deadline_decision`."""

    OK = "ok"
    EXPIRED = "expired"
    RENEWED = "renewed"


class Equivocation(Exception):  # noqa: N818
    """A second, DIFFERENT commit for a step already played."""


class ProtocolViolation(Exception):  # noqa: N818
    """An arrival past the reorder window."""


@dataclass
class InboxState:
    """State for the pure `delivery_decision` function."""

    played: dict[str, str] = field(default_factory=dict)
    window: int = 4
    next_step: int = 1


@dataclass
class Inbox:
    """Ordered delivery over an unordered, duplicating transport."""

    window: int = 4
    next_step: int = 1
    played: dict[int, str] = field(default_factory=dict)
    buffered: dict[int, dict] = field(default_factory=dict)
    absorbed: int = 0

    def __post_init__(self) -> None:
        if self.window <= 0:
            raise ValueError(f"window must be > 0, got {self.window}")

    def _state(self) -> dict:
        return {
            "played": {str(k): v for k, v in self.played.items()},
            "window": self.window,
            "next": self.next_step,
        }

    def offer(self, message: dict) -> list[dict]:
        """Take one inbound message; return messages ready to apply, in step order.

        An empty list means "nothing to do yet" — the message was a duplicate
        we absorbed, or it is buffered ahead of a gap. It never means
        "something went wrong": that is an exception.
        """
        arrival = {"step": int(message["step"]), "commit": message["commit"]}
        decision = delivery_decision(self._state(), arrival)

        if decision in (DeliveryDecision.ABSORB, DeliveryDecision.DISCARD):
            self.absorbed += 1
            return []
        if decision == DeliveryDecision.EQUIVOCATION_LOUD:
            raise Equivocation(
                f"step {arrival['step']} was already played under commit "
                f"{self.played[arrival['step']]}, and a DIFFERENT commit "
                f"{arrival['commit']} has now arrived for it."
            )
        if decision == DeliveryDecision.VIOLATION:
            raise ProtocolViolation(
                f"step {arrival['step']} is more than {self.window} ahead of "
                f"the next expected step ({self.next_step}) — past the reorder window."
            )
        if decision == DeliveryDecision.BUFFER:
            self.buffered[arrival["step"]] = message
            return []

        # "apply": take it, then drain whatever was waiting behind it.
        ready = [message]
        self.played[arrival["step"]] = arrival["commit"]
        self.next_step = arrival["step"] + 1
        while self.next_step in self.buffered:
            nxt = self.buffered.pop(self.next_step)
            self.played[self.next_step] = nxt["commit"]
            ready.append(nxt)
            self.next_step += 1
        return ready

    def reset_for_subgame(self) -> None:
        """Clear state for the next sub-game."""
        self.played.clear()
        self.buffered.clear()
        self.next_step = 1
        self.absorbed = 0


def delivery_decision(state: dict, arrival: dict) -> str:
    """Pure six-way decision function (FR-32).

    State  = {"played": {step: commit}, "window": int, "next": step}
    Arrival = {"step": int, "commit": str}
    """
    played = state["played"]
    step = arrival["step"]
    commit = arrival["commit"]

    # Check if already played — keyed on commit, not (kind, step).
    if str(step) in played or step in played:
        seen = played.get(str(step), played.get(step))
        return DeliveryDecision.ABSORB if seen == commit else DeliveryDecision.EQUIVOCATION_LOUD

    if step == state["next"]:
        return DeliveryDecision.APPLY_DRAIN
    if step < state["next"]:
        return DeliveryDecision.DISCARD
    if step - state["next"] <= state["window"]:
        return DeliveryDecision.BUFFER
    return DeliveryDecision.VIOLATION


def deadline_decision(deadline_at: float, now: float, arrived: bool, tolerated: bool) -> str:
    """Pure deadline judgment (FR-33).

    Returns "expired" or "ok". Tolerated traffic renews nothing.
    """
    del arrived, tolerated
    return DeadlineDecision.EXPIRED if now >= deadline_at else DeadlineDecision.OK
