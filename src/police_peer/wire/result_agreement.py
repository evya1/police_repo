"""Exchanging the settlement digest after the audit, before anyone reports (T058, CT-08).

Ordering matters and is not arbitrary. The mutual log audit runs first -- App. E rule 36 makes
it a precondition of agreeing on anything -- and only then do the two peers compare what they
settled on. Agreeing before auditing would be agreeing about an unverified game.

It rides the CONTROL lane. The agreement lane already carries greetings (per series and per
sub-game) and the turn lane carries the game; settlement is neither, and putting it on a lane
nothing else polls means a late greeting can never be mistaken for a settlement or vice versa.

This never raises into the caller. A series that has already been played and audited must not
be lost because the opponent went quiet during the settlement handshake: the bundle is still
publishable, it simply records `confirmed: false` and says why. Refusing to REPORT is a
separate decision, made by the reporting root.
"""

from __future__ import annotations

import logging
import time

from common.transport.kit_agreement import (
    AGREEMENT_KIND,
    AgreementOutcome,
    AgreementProposal,
    evaluate,
    proposal_wire,
)

logger = logging.getLogger(__name__)

#: How often we look for the opponent's proposal while waiting.
POLL_INTERVAL = 0.05


def _looks_like_proposal(message: object) -> bool:
    return isinstance(message, dict) and message.get("kind") == AGREEMENT_KIND


def exchange(channel, ours: AgreementProposal, *, budget: float) -> AgreementOutcome:
    """Send our proposal once, wait one budget for theirs, and decide."""
    try:
        channel.send_control(proposal_wire(ours))
    except Exception as exc:  # noqa: BLE001 - a played series is never lost to a send fault
        logger.warning("Could not send the result-agreement proposal: %s", exc)
        return AgreementOutcome(False, f"our proposal could not be sent: {exc}")

    deadline = time.monotonic() + budget
    while time.monotonic() < deadline:
        try:
            message = channel.poll_control()
        except Exception as exc:  # noqa: BLE001 - same reason
            logger.warning("Could not read a result-agreement proposal: %s", exc)
            return AgreementOutcome(False, f"their proposal could not be read: {exc}")
        if _looks_like_proposal(message):
            return evaluate(ours, message)
        time.sleep(POLL_INTERVAL)

    return AgreementOutcome(
        False,
        f"the opponent's proposal did not arrive within {budget:g}s, so nothing was agreed. "
        f"A timeout is not assent: reporting alone on an unconfirmed result is what rule 35 "
        f"punishes both sides for",
    )
