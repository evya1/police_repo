"""Regression tests for multiplicative_book_v1 against expected recurrence behavior.

Covers M-01 worked examples and saturation divergence between book and subtractive profiles.
"""

from __future__ import annotations

import pytest

from police_peer.scent.profiles.multiplicative_book_v1 import book_update


class TestBookRecurrenceWorkedExample:
    """M-01 §A worked example: 0.4 → 0.36 → 0.324.

    This is a regression for the book-side multiplicative recurrence, not a conformance vector.
    """

    def test_book_recurrence(self) -> None:
        tau = 0.0
        # t=1: emission delta = 0.4
        tau = book_update(tau, 0.4, 0.1, 0.9)
        assert tau == 0.4
        # t=2: no further emission
        tau = book_update(tau, 0.0, 0.1, 0.9)
        assert tau == pytest.approx(0.36)
        # t=3: no further emission
        tau = book_update(tau, 0.0, 0.1, 0.9)
        assert tau == pytest.approx(0.324)


class TestSaturationDivergence:
    """T005 L84: the two profiles genuinely differ on saturation."""

    def test_book_clamps_at_09(self) -> None:
        """Book profile: tau=0.9, delta=0.62 → 0.9 (clamped)."""
        result = book_update(0.9, 0.62, 0.1, 0.9)
        assert result == 0.9

    def test_subtractive_no_upper_clamp(self) -> None:
        """Subtractive profile: no upper clamp, max-merge only."""
        from police_peer.scent.profiles.subtractive_chebyshev_v1 import smell_decay

        # Start with tau=0.9 at a cell, then apply a subtractive decay + emit that would
        # push it above 0.9. Since subtractive uses max-merge and subtractive decay,
        # the result should be 0.9 (max-merge preserves the existing 0.9).
        # But the key difference: if we had a different starting value, the subtractive
        # profile would NOT clamp upward.
        # Test: start at 0.95 (simulating max-merge from a prior emission), decay by 0.1
        result = smell_decay({"0,0": 0.95}, 0.1)
        assert result["0,0"] == 0.85  # no upper clamp, just subtractive decay


class TestNoForgedScent:
    """M-01 STRAT-004: emission never occurs outside the kernel support."""

    def test_emission_within_kernel_support(self) -> None:
        from police_peer.scent.model import make_trail

        trail = make_trail(board_size=7, model="multiplicative_book_v1")
        center = (3, 3)
        result = trail.full_turn(center)
        for key in result:
            r, c = map(int, key.split(","))
            assert abs(r - center[0]) <= 2
            assert abs(c - center[1]) <= 2


class TestEdges:
    """Corner emissions and out-of-board clipping are deterministic and board-bounded."""

    def test_corner_emission_book(self) -> None:
        from police_peer.scent.model import make_trail

        trail = make_trail(board_size=7, model="multiplicative_book_v1")
        center = (0, 0)
        result = trail.full_turn(center)
        for key in result:
            r, c = map(int, key.split(","))
            assert 0 <= r < 7
            assert 0 <= c < 7
        # Verify the exact expected field from the fixture
        expected = {
            "0,0": 0.9, "0,1": 0.62, "0,2": 0.2,
            "1,0": 0.62, "1,1": 0.42, "1,2": 0.14,
            "2,0": 0.2, "2,1": 0.14, "2,2": 0.04,
        }
        assert result == expected
