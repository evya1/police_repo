"""Regression and property tests for BeliefGrid normalization and invariants.

Covers:
- Zero mass recovery preserves allowed-cell mask (never places mass on excluded/barrier cells)
- Deterministic failure when zero allowed cells remain
- Nonnegative values invariant
- Sum=1 normalization across arbitrary operations
- Deterministic hint properties
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief import build_belief
from police_peer.belief.grid import BeliefGrid
from police_peer.belief.hints import apply_hint, parse_landmarks
from police_peer.belief.update import apply_half_turn


class TestZeroMassExclusionPreservation:
    """BeliefGrid._normalize() never resets uniformly across excluded/barrier cells."""

    def test_zero_mass_preserves_excluded_cells(self) -> None:
        board = Board(size=7)
        bg = BeliefGrid(board)

        # Exclude specific cells
        excluded = {(0, 0), (1, 1), (3, 3), (6, 6)}
        for cell in excluded:
            bg.exclude(cell)

        # Confirm excluded cells are 0.0 before zero-mass event
        for cell in excluded:
            assert bg.prob(cell) == pytest.approx(0.0)

        # Force all cells in matrix to 0.0 (simulating evidence removing all allowed mass)
        for r in range(7):
            for c in range(7):
                bg._matrix[r][c] = 0.0

        # Renormalize should restore uniform mass ONLY to allowed cells
        bg._normalize()

        expected_allowed_count = 49 - len(excluded)
        expected_prob = 1.0 / expected_allowed_count

        for r in range(7):
            for c in range(7):
                if (r, c) in excluded:
                    assert bg.prob((r, c)) == pytest.approx(0.0)
                else:
                    assert bg.prob((r, c)) == pytest.approx(expected_prob)

        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)

    def test_zero_mass_during_apply_half_turn(self) -> None:
        """Zero mass after turn update keeps barrier and own cell excluded."""
        bg = BeliefGrid(Board(size=5))
        barrier = (2, 2)
        own_cell = (0, 0)

        apply_half_turn(
            bg,
            barrier=barrier,
            field={},
            hint="",
            arena="New York",
            own_cell=own_cell,
            capture_landed=False,
        )

        # Force matrix to zero
        for r in range(5):
            for c in range(5):
                bg._matrix[r][c] = 0.0

        bg._normalize()

        assert bg.prob(barrier) == pytest.approx(0.0)
        assert bg.prob(own_cell) == pytest.approx(0.0)

        # Sum over remaining 23 cells must be 1.0
        total = sum(bg.prob((r, c)) for r in range(5) for c in range(5))
        assert total == pytest.approx(1.0)

    def test_deterministic_failure_when_no_cells_remain(self) -> None:
        """When every cell on board is excluded, normalize raises ValueError deterministically."""
        bg = BeliefGrid(Board(size=3))
        for r in range(3):
            for c in range(3):
                if (r, c) != (2, 2):
                    bg.exclude((r, c))

        assert bg.prob((2, 2)) == pytest.approx(1.0)

        # Excluding the last cell must raise ValueError on normalization
        with pytest.raises(ValueError, match="No allowed cells remain on board"):
            bg.exclude((2, 2))


class TestNonnegativeAndSumInvariants:
    """Property checks: probabilities are non-negative and sum to 1."""

    def test_negative_values_clamped_and_normalized(self) -> None:
        bg = BeliefGrid(Board(size=5))
        for r in range(5):
            for c in range(5):
                bg._matrix[r][c] = 0.0
        bg._matrix[0][0] = -5.0
        bg._matrix[0][1] = -1.0
        bg._matrix[2][2] = 2.0
        bg._normalize()

        assert bg.prob((0, 0)) == pytest.approx(0.0)
        assert bg.prob((0, 1)) == pytest.approx(0.0)
        assert bg.prob((2, 2)) == pytest.approx(1.0)

        for r in range(5):
            for c in range(5):
                assert bg.prob((r, c)) >= 0.0

        total = sum(bg.prob((r, c)) for r in range(5) for c in range(5))
        assert total == pytest.approx(1.0)

    def test_repeated_diffusion_and_hints_sum_is_one(self) -> None:
        bg = BeliefGrid(Board(size=7))
        for _ in range(10):
            bg.diffuse()
            apply_hint(bg, "Times Square and Central Park", "New York", 7, 0.3)
            bg.observe_smell({"3,3": 0.5, "1,2": 0.8})
            total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
            assert total == pytest.approx(1.0, abs=1e-6)
            for r in range(7):
                for c in range(7):
                    assert bg.prob((r, c)) >= 0.0


class TestDeterministicHints:
    """Deterministic hint parsing and application."""

    def test_hint_determinism(self) -> None:
        bg1 = build_belief(Board(size=7), {"belief": {}}, probe=None)
        bg2 = build_belief(Board(size=7), {"belief": {}}, probe=None)

        hint = "suspect spotted near Central Park and Manhattan"
        apply_hint(bg1, hint, "New York", 7, 0.25)
        apply_hint(bg2, hint, "New York", 7, 0.25)

        assert bg1.as_matrix() == bg2.as_matrix()

    def test_parse_landmarks_order_dedup(self) -> None:
        res1 = parse_landmarks("The Bronx The Bronx Brooklyn", "New York", 7)
        res2 = parse_landmarks("The Bronx Brooklyn", "New York", 7)
        assert res1 == res2
