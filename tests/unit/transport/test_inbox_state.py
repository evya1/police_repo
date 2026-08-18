"""Tests for Inbox state management: reset, counters, and drain behavior."""

from __future__ import annotations

from common.transport.inbox import Inbox


def _make_turn(step: int, commit: str = "a" * 64) -> dict:
    return {"step": step, "commit": commit, "sender": "thief", "hint": "nearby"}


class TestInboxStateManagement:
    """Tests for Inbox reset and state tracking."""

    def test_reset_for_subgame_clears_all(self) -> None:
        inbox = Inbox()
        inbox.offer(_make_turn(1))
        inbox.offer(_make_turn(2))
        inbox.reset_for_subgame()
        assert inbox.played == {}
        assert inbox.buffered == {}
        assert inbox.next_step == 1
        assert inbox.absorbed == 0

    def test_reset_preserves_window(self) -> None:
        inbox = Inbox(window=8)
        inbox.reset_for_subgame()
        assert inbox.window == 8

    def test_absorbed_counter_increments(self) -> None:
        inbox = Inbox()
        inbox.offer(_make_turn(1))
        inbox.offer(_make_turn(1))  # duplicate
        inbox.offer(_make_turn(0))  # stale — discard
        assert inbox.absorbed == 2

    def test_buffered_cleaned_on_apply_drain(self) -> None:
        inbox = Inbox()
        inbox.offer(_make_turn(3))
        assert 3 in inbox.buffered
        inbox.offer(_make_turn(1))
        inbox.offer(_make_turn(2))
        # After applying 1, 2, 3 in sequence, buffer should be empty.
        assert inbox.buffered == {}
        assert inbox.next_step == 4

    def test_multiple_subgames_independent(self) -> None:
        inbox = Inbox()
        # Sub-game 1.
        inbox.offer(_make_turn(1))
        inbox.offer(_make_turn(2))
        inbox.reset_for_subgame()
        # Sub-game 2 — state is fresh.
        inbox.offer(_make_turn(1))
        assert inbox.played == {1: "a" * 64}
        assert inbox.next_step == 2

    def test_absorbed_resets_per_subgame(self) -> None:
        """Absorbed counter is reset per sub-game, matching the reference kit."""
        inbox = Inbox()
        inbox.offer(_make_turn(1))
        inbox.offer(_make_turn(1))  # absorbed
        assert inbox.absorbed == 1
        inbox.reset_for_subgame()
        # Counter is cleared for the new sub-game.
        assert inbox.absorbed == 0
