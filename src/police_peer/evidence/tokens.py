"""Honest token-usage events (T013, ADR-010).

Three explicit states -- never two:

- ``known_zero``: no provider call occurred, or the call reported exactly
  ``0``/``0``.
- ``known_nonzero``: the provider reported non-negative counts, at least one
  non-zero.
- ``unknown``: a call may have occurred but reliable counts are unavailable.
  ``unknown`` is never rewritten to ``0`` -- a deterministic fallback cannot
  erase tokens a provider may already have consumed.

This module builds validated per-step events; :mod:`police_peer.evidence.token_ledger`
owns aggregation. Nothing here infers a count from response text, and nothing
here decides move legality, capture, verdict, or score.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from police_peer.strategy.hint_types import HintResult

_MAX_TOKEN_COUNT = 10_000_000


class TokenAccountingError(Exception):
    """Base error for the evidence token-accounting boundary."""


class InvalidTokenCountError(TokenAccountingError):
    """A supplied token count is not a valid non-negative bounded integer."""


class UsageStatus(Enum):
    """The three explicit knowledge states for a token count."""

    KNOWN_ZERO = "known_zero"
    KNOWN_NONZERO = "known_nonzero"
    UNKNOWN = "unknown"


def _validate_count(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise InvalidTokenCountError(f"{field_name} must be an int, not bool")
    if not isinstance(value, int):
        raise InvalidTokenCountError(
            f"{field_name} must be an int, got {type(value).__name__}"
        )
    if value < 0:
        raise InvalidTokenCountError(f"{field_name} must be non-negative, got {value}")
    if value > _MAX_TOKEN_COUNT:
        raise InvalidTokenCountError(
            f"{field_name}={value} exceeds the maximum representable single-call count"
        )
    return value


def status_for_counts(input_tokens: int | None, output_tokens: int | None) -> UsageStatus:
    """Classify a raw (input, output) pair. ``None`` in either slot is unknown."""
    if input_tokens is None or output_tokens is None:
        return UsageStatus.UNKNOWN
    return UsageStatus.KNOWN_NONZERO if (input_tokens or output_tokens) else UsageStatus.KNOWN_ZERO


@dataclass(frozen=True, slots=True)
class TokenEvent:
    """One recorded usage observation for a single step of a single sub-game."""

    sub_game_id: str
    step: int
    counted: bool
    provider_called: bool
    fallback: bool
    status: UsageStatus
    input_tokens: int | None
    output_tokens: int | None

    def __post_init__(self) -> None:
        input_tokens = _validate_count(self.input_tokens, "input_tokens")
        output_tokens = _validate_count(self.output_tokens, "output_tokens")
        object.__setattr__(self, "input_tokens", input_tokens)
        object.__setattr__(self, "output_tokens", output_tokens)
        expected = status_for_counts(input_tokens, output_tokens)
        if self.status is not expected:
            raise InvalidTokenCountError(
                f"status {self.status.value!r} is inconsistent with counts "
                f"({input_tokens!r}, {output_tokens!r}); expected {expected.value!r}"
            )

    @property
    def key(self) -> tuple[str, int]:
        return (self.sub_game_id, self.step)

    def as_dict(self) -> dict[str, Any]:
        return {
            "sub_game_id": self.sub_game_id,
            "step": self.step,
            "counted": self.counted,
            "provider_called": self.provider_called,
            "fallback": self.fallback,
            "status": self.status.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


def event_from_hint_result(
    *, sub_game_id: str, step: int, counted: bool, hint_result: HintResult
) -> TokenEvent:
    """Build a :class:`TokenEvent` from a strategy ``HintResult`` (T027 boundary).

    A provider is considered "not called" only for ``NO_PROVIDER`` (no
    provider configured) or ``NON_CLAIM`` (a local-only branch that never
    reaches a provider); both contribute exactly ``0``/``0``. Every other
    fallback reason (timeout, exception, malformed, invalid text) means a
    call was attempted, so its usage -- known or unknown -- is preserved.
    """
    from police_peer.strategy.hint_types import FallbackReason

    provider_called = hint_result.fallback_reason not in (
        FallbackReason.NO_PROVIDER,
        FallbackReason.NON_CLAIM,
    )
    fallback = hint_result.fallback_reason is not None
    if provider_called:
        input_tokens = hint_result.usage.input_tokens
        output_tokens = hint_result.usage.output_tokens
    else:
        input_tokens = 0
        output_tokens = 0
    status = status_for_counts(input_tokens, output_tokens)
    return TokenEvent(
        sub_game_id=sub_game_id,
        step=step,
        counted=counted,
        provider_called=provider_called,
        fallback=fallback,
        status=status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
