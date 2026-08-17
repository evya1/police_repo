"""Tests for the pure `delivery_decision` function.

FR-32: the six-way pinned delivery table.
"""

from __future__ import annotations

from common.transport.inbox import DeliveryDecision, delivery_decision


def _make_turn(step: int, commit: str = "a" * 64) -> dict:
    return {"step": step, "commit": commit, "sender": "thief", "hint": "nearby"}


def _make_state(played: dict | None = None, *, window: int = 4, next_step: int = 1) -> dict:
    if played is None:
        played = {}
    return {
        "played": {str(k): v for k, v in played.items()},
        "window": window,
        "next": next_step,
    }


class TestDeliveryDecisionApply:
    """delivery_decision returns APPLY_DRAIN for the next expected step."""

    def test_apply_next(self) -> None:
        state = _make_state()
        assert delivery_decision(state, _make_turn(1)) == DeliveryDecision.APPLY_DRAIN

    def test_apply_after_previously_buffered(self) -> None:
        state = _make_state(played={1: "a" * 64}, next_step=2)
        assert delivery_decision(state, _make_turn(2)) == DeliveryDecision.APPLY_DRAIN


class TestDeliveryDecisionAbsorb:
    """delivery_decision returns ABSORB for an exact duplicate (same commit)."""

    def test_absorb_same_commit(self) -> None:
        state = _make_state(played={1: "abc"})
        assert delivery_decision(state, _make_turn(1, commit="abc")) == DeliveryDecision.ABSORB

    def test_absorb_with_string_key(self) -> None:
        """The played map uses string keys; lookup must handle both int and str."""
        state = _make_state(played={"1": "abc"})
        assert delivery_decision(state, _make_turn(1, commit="abc")) == DeliveryDecision.ABSORB


class TestDeliveryDecisionEquivocation:
    """delivery_decision returns EQUIVOCATION_LOUD for a different commit on a played step."""

    def test_equivocation_different_commit(self) -> None:
        state = _make_state(played={1: "abc"})
        assert delivery_decision(state, _make_turn(1, commit="xyz")) == DeliveryDecision.EQUIVOCATION_LOUD

    def test_no_equivocation_when_not_played(self) -> None:
        state = _make_state()
        # Step 1 not yet played — should apply, not equivocate.
        assert delivery_decision(state, _make_turn(1, commit="xyz")) == DeliveryDecision.APPLY_DRAIN


class TestDeliveryDecisionDiscard:
    """delivery_decision returns DISCARD for steps below next that were never played."""

    def test_discard_below_next(self) -> None:
        state = _make_state(played={}, next_step=3)
        assert delivery_decision(state, _make_turn(1)) == DeliveryDecision.DISCARD

    def test_discard_step_zero(self) -> None:
        """Step 0 is a voided attempt's leftover — always discarded."""
        state = _make_state(played={}, next_step=1)
        assert delivery_decision(state, _make_turn(0)) == DeliveryDecision.DISCARD


class TestDeliveryDecisionBuffer:
    """delivery_decision returns BUFFER for within-window out-of-order arrivals."""

    def test_buffer_within_window(self) -> None:
        state = _make_state(window=4)
        assert delivery_decision(state, _make_turn(3)) == DeliveryDecision.BUFFER

    def test_buffer_at_boundary(self) -> None:
        """Step exactly at window boundary is buffered, not violated."""
        state = _make_state(window=4)
        assert delivery_decision(state, _make_turn(5)) == DeliveryDecision.BUFFER


class TestDeliveryDecisionViolation:
    """delivery_decision returns VIOLATION for steps beyond the reorder window."""

    def test_violation_beyond_window(self) -> None:
        state = _make_state(window=4)
        assert delivery_decision(state, _make_turn(6)) == DeliveryDecision.VIOLATION

    def test_violation_far_ahead(self) -> None:
        state = _make_state(window=4)
        assert delivery_decision(state, _make_turn(100)) == DeliveryDecision.VIOLATION
