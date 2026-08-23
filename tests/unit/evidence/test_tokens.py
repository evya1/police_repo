"""Tests for honest per-step token-usage events (T013).

Covers status classification, count validation, and building a
:class:`TokenEvent` from a strategy ``HintResult`` for cases 1-7 of the
task packet's twelve required accounting cases (aggregation cases 8-12 live
in ``test_token_ledger.py``).
"""

from __future__ import annotations

import pytest

from police_peer.evidence.tokens import (
    InvalidTokenCountError,
    TokenEvent,
    UsageStatus,
    event_from_hint_result,
    status_for_counts,
)
from police_peer.strategy.hint_types import FallbackReason
from tests.unit.evidence.token_fixtures import make_event, make_hint_result


class TestStatusForCounts:
    def test_both_present_nonzero_is_known_nonzero(self) -> None:
        assert status_for_counts(5, 3) is UsageStatus.KNOWN_NONZERO

    def test_both_present_zero_is_known_zero(self) -> None:
        assert status_for_counts(0, 0) is UsageStatus.KNOWN_ZERO

    def test_either_missing_is_unknown(self) -> None:
        assert status_for_counts(None, 3) is UsageStatus.UNKNOWN
        assert status_for_counts(5, None) is UsageStatus.UNKNOWN
        assert status_for_counts(None, None) is UsageStatus.UNKNOWN


class TestTokenEventValidation:
    def test_negative_count_rejected(self) -> None:
        with pytest.raises(InvalidTokenCountError):
            make_event(input_tokens=-1, output_tokens=0)

    def test_bool_count_rejected(self) -> None:
        with pytest.raises(InvalidTokenCountError):
            TokenEvent(
                sub_game_id="g01",
                step=1,
                counted=True,
                provider_called=True,
                fallback=False,
                status=UsageStatus.KNOWN_NONZERO,
                input_tokens=True,
                output_tokens=1,
            )

    def test_non_integer_count_rejected(self) -> None:
        with pytest.raises(InvalidTokenCountError):
            TokenEvent(
                sub_game_id="g01",
                step=1,
                counted=True,
                provider_called=True,
                fallback=False,
                status=UsageStatus.KNOWN_NONZERO,
                input_tokens=1.5,  # type: ignore[arg-type]
                output_tokens=1,
            )

    def test_overflow_count_rejected(self) -> None:
        with pytest.raises(InvalidTokenCountError):
            make_event(input_tokens=10**9, output_tokens=0)

    def test_status_inconsistent_with_counts_rejected(self) -> None:
        with pytest.raises(InvalidTokenCountError):
            TokenEvent(
                sub_game_id="g01",
                step=1,
                counted=True,
                provider_called=True,
                fallback=False,
                status=UsageStatus.UNKNOWN,
                input_tokens=5,
                output_tokens=3,
            )


class TestEventFromHintResult:
    def test_case_1_no_provider_configured_is_known_zero(self) -> None:
        result = make_hint_result(FallbackReason.NO_PROVIDER, None, None)
        event = event_from_hint_result(sub_game_id="g01", step=1, counted=True, hint_result=result)
        assert event.provider_called is False
        assert event.status is UsageStatus.KNOWN_ZERO
        assert (event.input_tokens, event.output_tokens) == (0, 0)

    def test_case_2_non_claim_local_only_is_known_zero(self) -> None:
        result = make_hint_result(FallbackReason.NON_CLAIM, None, None)
        event = event_from_hint_result(sub_game_id="g01", step=1, counted=True, hint_result=result)
        assert event.provider_called is False
        assert event.status is UsageStatus.KNOWN_ZERO
        assert (event.input_tokens, event.output_tokens) == (0, 0)

    def test_case_3_accepted_reply_with_counts_is_exact(self) -> None:
        result = make_hint_result(None, 12, 8)
        event = event_from_hint_result(sub_game_id="g01", step=1, counted=True, hint_result=result)
        assert event.provider_called is True
        assert event.fallback is False
        assert event.status is UsageStatus.KNOWN_NONZERO
        assert (event.input_tokens, event.output_tokens) == (12, 8)

    def test_case_4_accepted_reply_without_counts_is_unknown(self) -> None:
        result = make_hint_result(None, None, None)
        event = event_from_hint_result(sub_game_id="g01", step=1, counted=True, hint_result=result)
        assert event.provider_called is True
        assert event.status is UsageStatus.UNKNOWN

    def test_case_5_rejected_reply_with_counts_is_fallback_plus_exact(self) -> None:
        result = make_hint_result(FallbackReason.MALFORMED, 9, 4)
        event = event_from_hint_result(sub_game_id="g01", step=1, counted=True, hint_result=result)
        assert event.provider_called is True
        assert event.fallback is True
        assert event.status is UsageStatus.KNOWN_NONZERO
        assert (event.input_tokens, event.output_tokens) == (9, 4)

    def test_case_6_rejected_reply_without_counts_is_fallback_plus_unknown(self) -> None:
        result = make_hint_result(FallbackReason.INVALID_TEXT, None, None)
        event = event_from_hint_result(sub_game_id="g01", step=1, counted=True, hint_result=result)
        assert event.provider_called is True
        assert event.fallback is True
        assert event.status is UsageStatus.UNKNOWN

    def test_case_7_timeout_after_dispatch_is_unknown(self) -> None:
        result = make_hint_result(FallbackReason.TIMEOUT, None, None)
        event = event_from_hint_result(sub_game_id="g01", step=1, counted=True, hint_result=result)
        assert event.provider_called is True
        assert event.status is UsageStatus.UNKNOWN

    def test_case_7_exception_with_reliable_lower_layer_counts_is_known(self) -> None:
        result = make_hint_result(FallbackReason.EXCEPTION, 3, 1)
        event = event_from_hint_result(sub_game_id="g01", step=1, counted=True, hint_result=result)
        assert event.provider_called is True
        assert event.status is UsageStatus.KNOWN_NONZERO
        assert (event.input_tokens, event.output_tokens) == (3, 1)
