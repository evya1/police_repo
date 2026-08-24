"""Append-only per-series token aggregation (T013, ADR-010).

Aggregates :class:`~police_peer.evidence.tokens.TokenEvent` records into
per-sub-game and per-series totals. Duplicate evidence for the same
``(sub_game_id, step)`` is idempotent when byte-identical to what is already
recorded, and raises otherwise -- it is never silently double-counted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.transport.canonical import canonical_bytes
from police_peer.evidence.tokens import TokenAccountingError, TokenEvent, UsageStatus


class DuplicateTokenEventError(TokenAccountingError):
    """Conflicting evidence was recorded twice for the same (sub_game, step)."""


class CountedPlayIneligibleError(TokenAccountingError):
    """Unknown counted-play usage exists and cannot be erased by fallback."""


@dataclass(frozen=True, slots=True)
class TokenTotal:
    """An aggregated total: a status plus the counts that back it.

    ``input_tokens``/``output_tokens`` are only meaningful when
    ``status is not UsageStatus.UNKNOWN``; an unknown total always reports
    ``0``/``0`` alongside the ``unknown`` status rather than a misleading
    partial sum.
    """

    status: UsageStatus
    input_tokens: int
    output_tokens: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


_ZERO_TOTAL = TokenTotal(UsageStatus.KNOWN_ZERO, 0, 0)
_UNKNOWN_TOTAL = TokenTotal(UsageStatus.UNKNOWN, 0, 0)


def _combine(events: list[TokenEvent]) -> TokenTotal:
    if not events:
        return _ZERO_TOTAL
    if any(event.status is UsageStatus.UNKNOWN for event in events):
        return _UNKNOWN_TOTAL
    total_in = sum(event.input_tokens or 0 for event in events)
    total_out = sum(event.output_tokens or 0 for event in events)
    status = UsageStatus.KNOWN_NONZERO if (total_in or total_out) else UsageStatus.KNOWN_ZERO
    return TokenTotal(status, total_in, total_out)


class TokenLedger:
    """Append-only per-series token accounting.

    Warmup events are recorded but excluded unless ``include_warmup=True``;
    counted readiness therefore never mistakes warmup evidence for league play.
    """

    def __init__(self) -> None:
        self._events: dict[tuple[str, int], TokenEvent] = {}

    def record(self, event: TokenEvent) -> None:
        existing = self._events.get(event.key)
        if existing is not None:
            if existing == event:
                return
            raise DuplicateTokenEventError(
                f"conflicting token evidence already recorded for sub_game={event.sub_game_id!r} "
                f"step={event.step}"
            )
        self._events[event.key] = event

    def _selected_events(
        self, *, sub_game_id: str | None = None, include_warmup: bool = False,
    ) -> list[TokenEvent]:
        return [
            event
            for event in self._events.values()
            if (include_warmup or event.counted)
            and (sub_game_id is None or event.sub_game_id == sub_game_id)
        ]

    def sub_game_total(self, sub_game_id: str, *, include_warmup: bool = False) -> TokenTotal:
        return _combine(self._selected_events(
            sub_game_id=sub_game_id, include_warmup=include_warmup,
        ))

    def series_total(self, *, include_warmup: bool = False) -> TokenTotal:
        return _combine(self._selected_events(include_warmup=include_warmup))

    def has_unknown_counted_usage(self) -> bool:
        return self.series_total().status is UsageStatus.UNKNOWN

    def sub_game_ids(self, *, include_warmup: bool = False) -> list[str]:
        return sorted({
            event.sub_game_id
            for event in self._selected_events(include_warmup=include_warmup)
        })

    def as_dict(self, *, include_warmup: bool = False) -> dict[str, Any]:
        return {
            "series_total": self.series_total(include_warmup=include_warmup).as_dict(),
            "per_sub_game": {
                sub_game_id: self.sub_game_total(
                    sub_game_id, include_warmup=include_warmup,
                ).as_dict()
                for sub_game_id in self.sub_game_ids(include_warmup=include_warmup)
            },
        }

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.as_dict())


def assert_counted_eligible(ledger: TokenLedger) -> None:
    """Fail closed: unknown counted-play usage makes counted play ineligible."""
    if ledger.has_unknown_counted_usage():
        raise CountedPlayIneligibleError(
            "counted play is ineligible: unknown token usage was recorded for this "
            "series and cannot be erased by a deterministic fallback"
        )
