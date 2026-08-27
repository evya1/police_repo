"""Outgoing negotiation greetings and their stable series-owned context."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from threading import Lock

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
    terms_snapshot = deepcopy(terms)
    locks_snapshot = deepcopy(locks) if locks is not None else {}
    identity_snapshot = deepcopy(identity_block) if identity_block is not None else {}
    uid = game_uid(terms_snapshot, group_id, opponent_group) if opponent_group else None
    greeting: dict = {
        "terms": terms_snapshot,
        "nonce": nonce,
        "signature": terms_signature(terms_snapshot, nonce),
        "group_id": group_id,
        "role": role,
        "sub_game_number": sub_game_number,
        "identity": {**identity_snapshot, "group_id": group_id, "role": role},
    }
    if uid is not None:
        greeting["game_uid"] = uid
    for family, key in (
        ("scent_model", "scent_model_sha256"),
        ("wire_shape", "wire_shape_sha256"),
        ("info_mode", "info_mode_sha256"),
        ("smell_binding", "smell_binding_sha256"),
    ):
        if locks_snapshot.get(family) is not None:
            greeting[key] = locks_snapshot[family]
    return greeting


@dataclass(frozen=True, slots=True)
class NegotiationContext:
    """Defensive value snapshot carried by every greeting from one peer."""

    terms: dict
    group_id: str
    locks: dict[str, str] | None = None
    identity_block: dict | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "terms", deepcopy(self.terms))
        object.__setattr__(self, "locks", deepcopy(self.locks))
        object.__setattr__(self, "identity_block", deepcopy(self.identity_block))

    def snapshot(self) -> NegotiationContext:
        """Return an independent copy so mutable dictionaries never cross ownership."""
        return NegotiationContext(
            terms=self.terms,
            group_id=self.group_id,
            locks=self.locks,
            identity_block=self.identity_block,
        )


class ConflictingGreetingError(ValueError):
    """The same series/sub-game was requested with incompatible declarations."""


@dataclass(frozen=True, slots=True)
class _GreetingSpecification:
    sub_game: int
    role: str
    opponent_group: str | None
    context: NegotiationContext
    nonce: str


@dataclass(slots=True)
class _CachedGreeting:
    specification: _GreetingSpecification
    message: dict


class SeriesGreetingSession:
    """Own stable outgoing greetings for exactly one game series."""

    __slots__ = ("_context", "_nonce_factory", "_greetings", "_lock")

    def __init__(
        self,
        context: NegotiationContext,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._context = context.snapshot()
        self._nonce_factory = nonce_factory
        self._greetings: dict[int, _CachedGreeting] = {}
        self._lock = Lock()

    @property
    def context(self) -> NegotiationContext:
        """Return a defensive view of the series-owned negotiation context."""
        return self._context.snapshot()

    def require_context(self, context: NegotiationContext) -> None:
        """Fail before negotiation if this session is reused with another config."""
        if context != self._context:
            raise ConflictingGreetingError("greeting session belongs to a different configuration")

    def build(
        self,
        *,
        sub_game: int,
        role: str,
        opponent_group: str | None = None,
    ) -> dict:
        """Return the one complete greeting established for this sub-game."""
        with self._lock:
            cached = self._greetings.get(sub_game)
            if cached is not None:
                spec = cached.specification
                if spec.role != role or spec.opponent_group != opponent_group:
                    raise ConflictingGreetingError(
                        f"sub-game {sub_game} greeting already established for "
                        f"role={spec.role!r}, opponent_group={spec.opponent_group!r}"
                    )
                return deepcopy(cached.message)

            nonce = (self._nonce_factory or new_nonce)()
            spec = _GreetingSpecification(
                sub_game=sub_game,
                role=role,
                opponent_group=opponent_group,
                context=self._context,
                nonce=nonce,
            )
            message = our_greeting(
                terms=self._context.terms,
                nonce=nonce,
                group_id=self._context.group_id,
                role=role,
                sub_game_number=sub_game,
                opponent_group=opponent_group,
                locks=self._context.locks,
                identity_block=self._context.identity_block,
            )
            self._greetings[sub_game] = _CachedGreeting(spec, message)
            return deepcopy(message)


# Temporary source compatibility for callers of the first T059 refactor.
GreetingFactory = SeriesGreetingSession
