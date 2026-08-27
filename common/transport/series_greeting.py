"""Series-opening greeting exchange, split from the series engine for the line cap."""

from __future__ import annotations

import time

from common.transport.greetings import NegotiationContext, SeriesGreetingSession
from common.transport.kit_identity import identity_from_greeting
from common.transport.negotiate import verify_greeting


def exchange_series_greeting(
    channel, config, name: str, opponent_pin, greetings: SeriesGreetingSession,
) -> tuple[str, str, str, dict | None]:
    """Exchange and verify sub-game one's greeting, returning resolved public identity."""
    expected = NegotiationContext(
        terms=config.terms, group_id=name, locks=config.locks,
        identity_block=config.identity_block,
    )
    greetings.require_context(expected)
    context = greetings.context
    greeting = greetings.build(sub_game=1, role=config.natural_role.value)
    channel.send_agreement(greeting)
    deadline = time.monotonic() + config.budgets.connect_timeout
    opponent = None
    while time.monotonic() < deadline:
        opponent = channel.poll_agreement()
        if opponent is not None:
            break
        time.sleep(config.budgets.poll_interval)
    if opponent is None:
        raise TimeoutError("opponent greeting not received")
    agreed = verify_greeting(
        opponent, context.terms, context.group_id, 1, our_locks=context.locks,
    )
    opponent_pin.bind(agreed.opponent_group, sub_game=1)
    return (
        agreed.game_id, agreed.game_uid, agreed.opponent_group,
        identity_from_greeting(opponent),
    )
