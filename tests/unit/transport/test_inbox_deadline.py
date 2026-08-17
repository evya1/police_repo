"""Tests for the pure `deadline_decision` function and TC-19.

FR-33: deadline semantics — duplicates/early pushes renew nothing;
judged every lap, not only on empty polls.
"""

from __future__ import annotations

from common.transport.inbox import DeadlineDecision, deadline_decision


class TestTc19DeadlineRenewsNothing:
    """TC-19: duplicate/early push renews nothing; deadline judged every lap."""

    def test_duplicate_does_not_renew_deadline(self) -> None:
        deadline_at = 100.0
        now = 50.0
        # A duplicate (arrived=True, tolerated=True) should not renew.
        result = deadline_decision(deadline_at, now, arrived=True, tolerated=True)
        assert result == DeadlineDecision.OK

    def test_expired_when_now_past_deadline(self) -> None:
        deadline_at = 100.0
        now = 100.0
        assert deadline_decision(deadline_at, now, arrived=False, tolerated=False) == DeadlineDecision.EXPIRED

    def test_expired_when_now_exactly_deadline(self) -> None:
        deadline_at = 100.0
        now = 100.0
        assert deadline_decision(deadline_at, now, arrived=False, tolerated=False) == DeadlineDecision.EXPIRED

    def test_waiting_when_now_before_deadline(self) -> None:
        deadline_at = 100.0
        now = 99.9
        assert deadline_decision(deadline_at, now, arrived=False, tolerated=False) == DeadlineDecision.OK

    def test_flood_does_not_renew(self) -> None:
        deadline_at = 100.0
        # Even with many tolerated messages, the deadline doesn't move.
        for _ in range(10):
            result = deadline_decision(deadline_at, 50.0, arrived=True, tolerated=True)
            assert result == DeadlineDecision.OK
        # Deadline still hasn't changed.
        assert deadline_decision(deadline_at, 99.9, arrived=False, tolerated=False) == DeadlineDecision.OK


class TestDeadlineDecisionPure:
    """Unit tests for the pure `deadline_decision` function."""

    def test_ok_before_deadline(self) -> None:
        assert deadline_decision(100.0, 50.0, False, False) == DeadlineDecision.OK

    def test_expired_at_deadline(self) -> None:
        assert deadline_decision(100.0, 100.0, False, False) == DeadlineDecision.EXPIRED

    def test_expired_past_deadline(self) -> None:
        assert deadline_decision(100.0, 150.0, False, False) == DeadlineDecision.EXPIRED

    def test_arrived_does_not_affect_result(self) -> None:
        # arrived is ignored — the contract says duplicates renew nothing.
        assert deadline_decision(100.0, 50.0, True, False) == DeadlineDecision.OK

    def test_tolerated_does_not_affect_result(self) -> None:
        # tolerated is ignored — the contract says tolerated traffic renews nothing.
        assert deadline_decision(100.0, 50.0, False, True) == DeadlineDecision.OK

    def test_no_renewal_on_arrived_and_tolerated(self) -> None:
        # Both arrived and tolerated are ignored together.
        assert deadline_decision(100.0, 50.0, True, True) == DeadlineDecision.OK
