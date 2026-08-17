"""Tests for window enforcement and out-of-order buffering.

TC-16: within-window out-of-order buffered and applied in sequence;
beyond window rejected with ProtocolViolation.
"""

from __future__ import annotations

import pytest

from common.transport.inbox import Inbox, ProtocolViolation


def _make_turn(step: int, commit: str = "a" * 64) -> dict:
    return {"step": step, "commit": commit, "sender": "thief", "hint": "nearby"}


class TestTc16WindowAndBuffer:
    """TC-16: within-window out-of-order buffered and applied in sequence; beyond window rejected."""

    def test_out_of_order_within_window_buffered(self) -> None:
        inbox = Inbox()
        # Send step 3 before step 2 — should be buffered.
        ready = inbox.offer(_make_turn(3))
        assert ready == []
        assert 3 in inbox.buffered

    def test_buffered_applied_when_gap_filled(self) -> None:
        inbox = Inbox()
        # Apply step 1 first so next advances.
        inbox.offer(_make_turn(1))
        # Send step 3 — should be buffered (gap at 2).
        inbox.offer(_make_turn(3))
        # Now send step 2 — should apply 2 and drain 3.
        ready = inbox.offer(_make_turn(2))
        assert len(ready) == 2
        assert ready[0]["step"] == 2
        assert ready[1]["step"] == 3
        assert inbox.next_step == 4

    def test_out_of_order_beyond_window_raises(self) -> None:
        inbox = Inbox()
        # Step 10 when next is 1 and window is 4 — violation.
        with pytest.raises(ProtocolViolation, match="past the reorder window"):
            inbox.offer(_make_turn(10))

    def test_window_zero_refused_at_load(self) -> None:
        with pytest.raises(ValueError, match="window must be > 0"):
            Inbox(window=0)

    def test_window_minus_one_refused(self) -> None:
        with pytest.raises(ValueError, match="window must be > 0"):
            Inbox(window=-1)

    def test_boundary_step_accepted(self) -> None:
        inbox = Inbox(window=4)
        # Step 5 when next is 1: 5 - 1 = 4 <= 4 => buffer.
        ready = inbox.offer(_make_turn(5))
        assert ready == []
        assert 5 in inbox.buffered

    def test_step_one_beyond_boundary_violation(self) -> None:
        inbox = Inbox(window=4)
        # Step 6 when next is 1: 6 - 1 = 5 > 4 => violation.
        with pytest.raises(ProtocolViolation):
            inbox.offer(_make_turn(6))
