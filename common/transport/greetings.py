"""Outgoing negotiation greetings and their stable series-owned context."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from common.transport.ids import game_uid, terms_signature
from common.transport.integrity import new_nonce


def our_greeting(
    terms: dict,
    nonce: str,
    group_id: str,
    role: str,
    sub_game_number: int,
    opponent_group: str | None = None,
    locks: dict[str, str] | None = None,
    identity_block: dict | None = None,
) -> dict:
    """Build an outgoing greeting, omitting optional values that were not declared."""
    locks = locks or {}
    uid = game_uid(terms, group_id, opponent_group) if opponent_group else None
    greeting: dict = {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "group_id": group_id,
        "role": role,
        "sub_game_number": sub_game_number,
        "identity": {**(identity_block or {}), "group_id": group_id, "role": role},
    }
    if uid is not None:
        greeting["game_uid"] = uid
    for family, key in (
        ("scent_model", "scent_model_sha256"),
        ("wire_shape", "wire_shape_sha256"),
        ("info_mode", "info_mode_sha256"),
        ("smell_binding", "smell_binding_sha256"),
    ):
        if locks.get(family) is not None:
            greeting[key] = locks[family]
    return greeting


@dataclass(frozen=True, slots=True)
class NegotiationContext:
    """Stable declarations carried by every greeting from one peer."""

    terms: dict
    group_id: str
    locks: dict[str, str] | None = None
    identity_block: dict | None = None


class GreetingFactory:
    """Build greetings while owning one lazily-created nonce per sub-game."""

    __slots__ = ("context", "_nonce_factory", "_nonces")

    def __init__(
        self,
        context: NegotiationContext,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self.context = context
        self._nonce_factory = nonce_factory
        self._nonces: dict[int, str] = {}

    def nonce_for_sub_game(self, sub_game: int) -> str:
        """Return a stable nonce, creating it only on the sub-game's first use."""
        if sub_game not in self._nonces:
            generator = self._nonce_factory or new_nonce
            self._nonces[sub_game] = generator()
        return self._nonces[sub_game]

    def build(
        self,
        *,
        sub_game: int,
        role: str,
        opponent_group: str | None = None,
    ) -> dict:
        """Build one greeting from stable context plus request-varying values."""
        return our_greeting(
            terms=self.context.terms,
            nonce=self.nonce_for_sub_game(sub_game),
            group_id=self.context.group_id,
            role=role,
            sub_game_number=sub_game,
            opponent_group=opponent_group,
            locks=self.context.locks,
            identity_block=self.context.identity_block,
        )
