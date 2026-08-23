"""Shared builders for token-evidence tests (T013)."""

from __future__ import annotations

from police_peer.evidence.tokens import TokenEvent, status_for_counts
from police_peer.strategy.hint_types import FallbackReason, HintResult, TokenUsage


def make_event(
    sub_game_id: str = "g01",
    step: int = 1,
    counted: bool = True,
    provider_called: bool = False,
    fallback: bool = False,
    input_tokens: int | None = 0,
    output_tokens: int | None = 0,
) -> TokenEvent:
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


def make_hint_result(
    fallback_reason: FallbackReason | None,
    input_tokens: int | None,
    output_tokens: int | None,
) -> HintResult:
    return HintResult(
        text="north of the old bridge",
        verdict="fallback" if fallback_reason is not None else "accepted",
        fallback_reason=fallback_reason,
        usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
    )
