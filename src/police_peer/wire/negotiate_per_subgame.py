"""Per-sub-game negotiation driver (SPEC 7.2/7.3, ADR-011, T052).

`PeerFacade.run()` already sends one greeting before its six-sub-game loop
(`common/transport/series.py::_exchange_greeting`, sub_game_number=1, our
natural role -- which already equals `role_for(natural, 1)` since odd
sub-games play the natural role). That exchange *is* sub-game 1's own
handshake. This module supplies the `SubgameDriver` `PeerFacade` calls once
per sub-game so that sub-games 2 through 6 each get one more real handshake
of their own before play -- one handshake per sub-game overall, never a
second one stacked in front of sub-game 1 and never one merely before the
series.

`game_uid` declaration is PROPOSED (SPEC 7.3): the first sub-game this driver
itself negotiates (sub-game 2) omits it, since the opponent group is not yet
pinned from this driver's own point of view; sub-games 3-6 declare the
derived value once the first opponent seen here is pinned, and a declared
mismatch refuses. `role`/`sub_game_number` pairing is PROMOTED: a comparable
mismatch refuses.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from common.domain.scoring import role_for
from common.transport.integrity import new_nonce
from common.transport.negotiate import our_greeting, verify_greeting
from common.transport.refusals import Refused
from common.transport.replay_evidence import SubgameDriver, default_subgame_driver
from common.transport.series import PeerConfig, SeriesRow


@dataclass
class _OpponentPin:
    """The opponent group this driver has itself verified, or None until pinned."""

    group: str | None = None


def negotiated_subgame_driver(group_id: str, inner: SubgameDriver | None = None) -> SubgameDriver:
    """Build a `SubgameDriver` that negotiates before every sub-game after the first."""
    inner_driver = inner or default_subgame_driver()
    pin = _OpponentPin()

    def _driver(channel, engine, config: PeerConfig, sub_game: int, *, evidence_sink=None) -> SeriesRow:
        if sub_game > 1:
            _negotiate_subgame(channel, config, group_id, sub_game, pin)
        return inner_driver(channel, engine, config, sub_game, evidence_sink=evidence_sink)

    return _driver


def _negotiate_subgame(channel, config: PeerConfig, group_id: str, sub_game: int, pin: _OpponentPin) -> None:
    """Send our per-sub-game greeting, wait for the opponent's, and verify it (FR-13 order),
    then enforce the two checks the common `verify_greeting` deliberately leaves silent:
    complementary role, and opponent-pin stability across the series."""
    role = role_for(config.natural_role, sub_game)
    greeting = our_greeting(
        terms=config.terms,
        nonce=new_nonce(),
        group_id=group_id,
        role=role.value,
        sub_game_number=sub_game,
        opponent_group=pin.group,
        locks=config.locks,
    )
    channel.send_agreement(greeting)
    opponent = _await_greeting(channel, config)
    agreed = verify_greeting(opponent, config.terms, group_id, sub_game, our_locks=config.locks)

    their_role = opponent.get("role")
    if their_role == role.value:
        raise Refused(
            "SPAR-N07",
            f"sub-game {sub_game}: role collision -- both peers declared {role.value!r}",
        )

    if pin.group is None:
        pin.group = agreed.opponent_group
    elif pin.group != agreed.opponent_group:
        raise Refused(
            "SPAR-N10",
            f"opponent changed mid-series: pinned {pin.group!r}, sub-game {sub_game} "
            f"greeting names {agreed.opponent_group!r} -- refused, not silently re-pinned",
        )


def _await_greeting(channel, config: PeerConfig) -> dict:
    """Poll for the opponent's greeting until it arrives or the connect budget runs out."""
    deadline = time.monotonic() + config.budgets.connect_timeout
    while time.monotonic() < deadline:
        opponent = channel.poll_agreement()
        if opponent is not None:
            return opponent
        time.sleep(config.budgets.poll_interval)
    raise TimeoutError("opponent sub-game greeting not received")
