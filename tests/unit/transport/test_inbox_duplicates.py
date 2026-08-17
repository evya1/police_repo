"""Tests for duplicate absorption and equivocation detection.

TC-14: exact duplicate absorbed; applied once; ledger unchanged.
TC-15: different commit for a played step => Equivocation, quarantined, loud.
"""

from __future__ import annotations

import pytest

from common.transport.inbox import Equivocation, Inbox


def _make_turn(step: int, commit: str = "a" * 64) -> dict:
    return {"step": step, "commit": commit, "sender": "thief", "hint": "nearby"}


# --- TC-14: exact duplicate absorbed; applied once; ledger unchanged -------------------


class TestTc14DuplicateAbsorbed:
    """TC-14: exact duplicate turn (same step, same commit) is absorbed; applied once."""

    def test_first_arrival_applied(self) -> None:
        inbox = Inbox()
        msg = _make_turn(1)
        ready = inbox.offer(msg)
        assert len(ready) == 1
        assert ready[0]["step"] == 1

    def test_exact_duplicate_absorbed(self) -> None:
        inbox = Inbox()
        msg = _make_turn(1)
        inbox.offer(msg)
        # Same message arrives again — should be absorbed, not re-applied.
        ready = inbox.offer(msg)
        assert ready == []
        assert inbox.absorbed == 1

    def test_ledger_unchanged_after_duplicate(self) -> None:
        inbox = Inbox()
        msg = _make_turn(1)
        inbox.offer(msg)
        inbox.offer(msg)
        # Only one step should be in the played map.
        assert len(inbox.played) == 1
        assert inbox.next_step == 2

    def test_duplicate_with_different_step_not_absorbed(self) -> None:
        inbox = Inbox()
        inbox.offer(_make_turn(1))
        # Different step, same commit — this is a different turn, not a duplicate.
        msg = _make_turn(2, commit="a" * 64)
        ready = inbox.offer(msg)
        assert len(ready) == 1
        assert ready[0]["step"] == 2


# --- TC-15: different commit for played step => Equivocation, quarantined, loud ---------


class TestTc15Equivocation:
    """TC-15: different commit for an already-played step => Equivocation exception."""

    def test_different_commit_raises(self) -> None:
        inbox = Inbox()
        inbox.offer(_make_turn(1, commit="a" * 64))
        with pytest.raises(Equivocation, match="DIFFERENT commit"):
            inbox.offer(_make_turn(1, commit="b" * 64))

    def test_played_map_unchanged_after_equivocation(self) -> None:
        inbox = Inbox()
        inbox.offer(_make_turn(1, commit="a" * 64))
        with pytest.raises(Equivocation):
            inbox.offer(_make_turn(1, commit="b" * 64))
        # Original commit still stands — the equivocation is quarantined.
        assert inbox.played[1] == "a" * 64
        assert inbox.next_step == 2

    def test_equivocation_message_names_the_steps(self) -> None:
        inbox = Inbox()
        inbox.offer(_make_turn(1, commit="abc"))
        with pytest.raises(Equivocation, match="step 1"):
            inbox.offer(_make_turn(1, commit="xyz"))
