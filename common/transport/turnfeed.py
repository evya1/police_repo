"""Feeding the transport into the ordered inbox, and reconciling sub-game boundaries.

Split out of ``subgame.py`` so that module owns only the exchange loop. Two rules live
here: every inbound message is validated before it reaches the inbox (FR-25), and the
tail of a finished sub-game never enters the next one's reorder window (rule 35).
"""

from __future__ import annotations

import time
from collections.abc import Callable

from common.transport.inbox import Inbox
from common.transport.refusals import Refused
from common.transport.validators import validate_turn


def _accept(msg: object, board_size: int) -> dict:
    """Validate one inbound turn, or refuse the whole turn (FR-25)."""
    verdict = validate_turn(msg, board_size=board_size)
    if verdict != "accept":
        raise Refused("SPAR-N11", verdict)
    return msg  # type: ignore[return-value]


def reconcile_subgame_boundary(
    channel, inbox: Inbox, applied: dict[int, dict], board_size: int,
) -> int:
    """Drop the previous sub-game's tail before the new window opens; return the count.

    The peer that settles owes one last sealed STAY so both ledgers record the same final
    step (rule 35), but its opponent breaks out of the loop the moment it has settled and
    never reads it. That message is still in the transport when the next sub-game starts,
    and a fresh ``Inbox`` rightly rejects it as past the reorder window.

    Only a step-1 message can belong to the NEW sub-game — the opponent cannot have sent a
    step 2 before seeing our step 1 — so a step-1 message is handed to the fresh inbox and
    everything above it is the finished sub-game's tail and is dropped here. Validation
    still runs first: a boundary is not an excuse to absorb a malformed turn.
    """
    dropped = 0
    while (msg := channel.poll_turn()) is not None:
        message = _accept(msg, board_size)
        if int(message["step"]) == 1:
            for ready in inbox.offer(message):
                applied[int(ready["step"])] = ready
        else:
            dropped += 1
    return dropped


def wait_for_step(
    channel, inbox: Inbox, applied: dict[int, dict], step: int, budgets, board_size: int,
) -> None:
    """Feed the turn channel into the inbox until the opponent's `step` move has applied.

    Every inbound message is validated (FR-25) before it ever reaches ``inbox.offer`` —
    the only mutation point for delivery state — so a malformed turn is refused with
    zero partial mutation instead of corrupting the reorder window.
    """
    deadline = time.monotonic() + budgets.turn_timeout
    while time.monotonic() < deadline:
        while (msg := channel.poll_turn()) is not None:
            message = _accept(msg, board_size)
            for ready in inbox.offer(message):
                applied[int(ready["step"])] = ready
        if step in applied:
            return
        time.sleep(budgets.poll_interval)
    raise TimeoutError(f"timed out waiting for opponent turn {step}")


def wait_for_reveal(
    channel, inbox: Inbox, applied: dict[int, dict], step: int, budgets, board_size: int,
    settled: Callable[[], object] | None = None,
) -> bool:
    """Wait for the opponent's `step`; return False when a settled peer owes nothing more.

    ``settled`` is consulted ONLY after the deadline has passed, and only where the caller
    knows a mirror step may never be owed: SPEC 3.1 lets two peers' ledgers differ by
    exactly one terminal step, so a thief whose own step already reached the survival
    threshold finishes without a police step of the same number. Everywhere else
    (``settled=None``, the default, which is a plain strict wait), and wherever our own
    state does NOT settle the sub-game, the opponent has simply gone silent and the
    ``TimeoutError`` stands.
    """
    try:
        wait_for_step(channel, inbox, applied, step, budgets, board_size)
    except TimeoutError:
        if settled is None or settled() is None:
            raise
        return False
    return True


def wait_audit(channel, budgets) -> dict | None:
    """Poll for the opponent's audit payload until deadline."""
    deadline = time.monotonic() + budgets.turn_timeout
    while time.monotonic() < deadline:
        msg = channel.poll_audit()
        if msg is not None:
            return msg
        time.sleep(budgets.poll_interval)
    return None
