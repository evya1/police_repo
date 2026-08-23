"""The one opponent a series is bound to, from the first verified greeting onward (T054).

A six-sub-game series plays exactly one opponent. Two code paths verify greetings --
``PeerFacade._exchange_greeting`` for sub-game 1 and the per-sub-game negotiation driver
for sub-games 2-6 -- and before T054 each kept its *own* pin. The driver's started empty,
so the first group it saw was sub-game 2's: a swap there was adopted as the pin instead of
refused against sub-game 1's. Only sub-games 3-6 were then compared, and to the wrong
group.

This object is that pin, owned once by the series and shared by both paths. It is
deliberately mutable-but-encapsulated rather than frozen: the pin is genuinely series
lifecycle state, and making the ownership explicit is the point (AGENTS.md, "make
mutable-state ownership explicit"). It holds no lock -- one series runs its greetings on
one thread, in order.
"""

from __future__ import annotations

from common.transport.refusals import Refused


class OpponentPin:
    """The opponent group this series verified first, or unset until the first greeting."""

    __slots__ = ("_group",)

    def __init__(self, group: str | None = None) -> None:
        self._group = group

    @property
    def group(self) -> str | None:
        """The pinned group, or None before the first verified greeting."""
        return self._group

    def bind(self, group: str, *, sub_game: int) -> None:
        """Establish the pin, or refuse a greeting that names a different opponent.

        Establishing is idempotent for the same group: a re-greeting by the same peer is
        ordinary, and only a genuine *change* is a refusal. The refusal is raised before
        the caller mutates any game state, so a swapped opponent never gets a half-played
        sub-game.
        """
        if self._group is None:
            self._group = group
            return
        if self._group != group:
            raise Refused(
                "SPAR-N10",
                f"opponent changed mid-series: pinned {self._group!r}, sub-game {sub_game} "
                f"greeting names {group!r} -- refused, not silently re-pinned",
            )
