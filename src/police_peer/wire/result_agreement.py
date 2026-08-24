"""Exchange the mutual result-agreement proposal once, over the existing control channel (CT-08).

This never raises into the game loop: a silent opponent, a malformed reply, or a timeout all
become an ``AgreementOutcome(agreed=False, ...)`` like any other disagreement, so the caller's
own reporting path -- not this module -- decides what a non-agreement means for it.
"""

from __future__ import annotations

import time

from common.transport.kit_agreement import (
    AgreementOutcome,
    AgreementProposal,
    evaluate,
    proposal_wire,
)


def exchange(channel, ours: AgreementProposal, *, budget: float) -> AgreementOutcome:
    """Send our proposal once; wait up to ``budget`` seconds for the opponent's; evaluate.

    ``channel`` is any object exposing ``send_control(message)`` / ``poll_control()`` -- the
    same generic control lane the series' loopback and MCP channels already provide. No retry
    beyond whatever the channel's own transport layer performs on ``send_control`` itself.
    """
    try:
        channel.send_control(proposal_wire(ours))
    except Exception as exc:  # noqa: BLE001 - a transport fault is a non-agreement, not a crash
        return AgreementOutcome(False, f"could not send our proposal: {exc}")

    deadline = time.monotonic() + budget
    theirs_wire: dict | None = None
    while time.monotonic() < deadline:
        try:
            message = channel.poll_control()
        except Exception:  # noqa: BLE001 - a poll fault is treated as "nothing arrived yet"
            message = None
        if isinstance(message, dict) and message.get("kind") == "result_agreement":
            theirs_wire = message
            break
        if message is not None:
            continue  # some other control message; keep waiting for ours
        time.sleep(0.01)

    if theirs_wire is None:
        return AgreementOutcome(
            False, f"opponent proposal did not arrive within {budget:g}s"
        )
    return evaluate(ours, theirs_wire)
