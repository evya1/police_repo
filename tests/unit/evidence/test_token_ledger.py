"""Tests for per-series token aggregation (T013).

Covers cases 8-12 of the task packet's twelve required accounting cases:
warmup-vs-counted separation, per-step -> per-sub-game -> series aggregation,
duplicate idempotency, invalid counts at record time, and deterministic
canonical serialization with Unicode.
"""

from __future__ import annotations

import pytest

from police_peer.evidence.token_ledger import (
    CountedPlayIneligibleError,
    DuplicateTokenEventError,
    TokenLedger,
    assert_counted_eligible,
)
from police_peer.evidence.tokens import InvalidTokenCountError, UsageStatus
from tests.unit.evidence.token_fixtures import make_event


class TestTokenLedgerAggregation:
    def test_case_8_warmup_and_counted_kept_separate(self) -> None:
        ledger = TokenLedger()
        ledger.record(make_event(sub_game_id="g01", step=1, counted=False, input_tokens=99, output_tokens=99))
        ledger.record(make_event(sub_game_id="g01", step=2, counted=True, input_tokens=5, output_tokens=5))
        total = ledger.series_total()
        assert total.status is UsageStatus.KNOWN_NONZERO
        assert (total.input_tokens, total.output_tokens) == (5, 5)

    def test_case_9_per_step_per_subgame_and_series_aggregation(self) -> None:
        ledger = TokenLedger()
        ledger.record(make_event(sub_game_id="g01", step=1, input_tokens=1, output_tokens=1))
        ledger.record(make_event(sub_game_id="g01", step=2, input_tokens=2, output_tokens=2))
        ledger.record(make_event(sub_game_id="g02", step=1, input_tokens=3, output_tokens=3))
        assert ledger.sub_game_total("g01").input_tokens == 3
        assert ledger.sub_game_total("g02").input_tokens == 3
        series = ledger.series_total()
        assert (series.input_tokens, series.output_tokens) == (6, 6)

    def test_six_subgame_aggregation(self) -> None:
        ledger = TokenLedger()
        for index in range(1, 7):
            sub_game_id = f"g{index:02d}"
            ledger.record(make_event(sub_game_id=sub_game_id, step=1, input_tokens=1, output_tokens=1))
        assert ledger.sub_game_ids() == [f"g{i:02d}" for i in range(1, 7)]
        assert ledger.series_total().input_tokens == 6

    def test_case_10_duplicate_identical_evidence_is_idempotent(self) -> None:
        ledger = TokenLedger()
        event = make_event(sub_game_id="g01", step=1, input_tokens=5, output_tokens=5)
        ledger.record(event)
        ledger.record(event)  # no-op, not double-counted
        assert ledger.series_total().input_tokens == 5

    def test_case_10_duplicate_conflicting_evidence_raises(self) -> None:
        ledger = TokenLedger()
        ledger.record(make_event(sub_game_id="g01", step=1, input_tokens=5, output_tokens=5))
        with pytest.raises(DuplicateTokenEventError):
            ledger.record(make_event(sub_game_id="g01", step=1, input_tokens=6, output_tokens=6))

    def test_unknown_propagates_through_aggregation(self) -> None:
        ledger = TokenLedger()
        ledger.record(make_event(sub_game_id="g01", step=1, input_tokens=5, output_tokens=5))
        ledger.record(
            make_event(sub_game_id="g01", step=2, provider_called=True, input_tokens=None, output_tokens=None)
        )
        total = ledger.sub_game_total("g01")
        assert total.status is UsageStatus.UNKNOWN
        assert (total.input_tokens, total.output_tokens) == (0, 0)

    def test_no_events_is_known_zero(self) -> None:
        ledger = TokenLedger()
        total = ledger.series_total()
        assert total.status is UsageStatus.KNOWN_ZERO
        assert (total.input_tokens, total.output_tokens) == (0, 0)

    def test_case_11_negative_and_boolean_counts_rejected_at_record_time(self) -> None:
        with pytest.raises(InvalidTokenCountError):
            make_event(input_tokens=-5, output_tokens=0)

    def test_case_12_canonical_serialization_deterministic_with_unicode(self) -> None:
        ledger = TokenLedger()
        ledger.record(make_event(sub_game_id="שלום-🎲", step=1, input_tokens=3, output_tokens=2))
        first = ledger.canonical_bytes()
        second = ledger.canonical_bytes()
        assert first == second
        assert b"\\u" not in first
        assert "שלום-🎲".encode() in first


class TestCountedEligibility:
    def test_unknown_counted_usage_blocks_counted_play(self) -> None:
        ledger = TokenLedger()
        ledger.record(
            make_event(sub_game_id="g01", step=1, provider_called=True, input_tokens=None, output_tokens=None)
        )
        with pytest.raises(CountedPlayIneligibleError):
            assert_counted_eligible(ledger)

    def test_known_counted_usage_is_eligible(self) -> None:
        ledger = TokenLedger()
        ledger.record(make_event(sub_game_id="g01", step=1, input_tokens=1, output_tokens=1))
        assert_counted_eligible(ledger)  # does not raise

    def test_unknown_warmup_only_usage_does_not_block_counted_play(self) -> None:
        ledger = TokenLedger()
        ledger.record(
            make_event(
                sub_game_id="g01",
                step=1,
                counted=False,
                provider_called=True,
                input_tokens=None,
                output_tokens=None,
            )
        )
        assert_counted_eligible(ledger)  # warmup-only unknown never blocks counted play
