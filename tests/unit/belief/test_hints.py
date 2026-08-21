"""Hint channel tests: landmark parsing and application.

Covers TC-B10, TC-B11.
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief import build_belief
from police_peer.belief.hints import (
    GENERIC_FALLBACK,
    LANDMARK_CELLS,
    apply_hint,
    parse_landmarks,
)


class TestParseLandmarks:
    """Landmark parsing is case-insensitive and pure."""

    def test_times_square_match(self) -> None:
        cells = parse_landmarks("I am near Times Square", "New York", 7)
        assert (3, 3) in cells
        assert (3, 4) in cells
        assert (4, 3) in cells

    def test_case_insensitive(self) -> None:
        cells1 = parse_landmarks("near times square", "New York", 7)
        cells2 = parse_landmarks("near TIMES SQUARE", "New York", 7)
        assert cells1 == cells2

    def test_no_match(self) -> None:
        cells = parse_landmarks("I am nowhere", "New York", 7)
        assert cells == []

    def test_generic_fallback(self) -> None:
        cells = parse_landmarks("I am in the center", "Some Random Arena", 7)
        assert (3, 3) in cells

    def test_compass_north(self) -> None:
        cells = parse_landmarks("go north", "Unknown", 7)
        assert (0, 3) in cells

    def test_compass_south(self) -> None:
        cells = parse_landmarks("go south", "Unknown", 7)
        assert (6, 3) in cells

    def test_unknown_arena_no_match(self) -> None:
        cells = parse_landmarks("The Bronx is great", "Unknown", 7)
        assert cells == []


class TestApplyHint:
    """TC-B10: hint application moves peak toward landmark region."""

    def test_hint_moves_peak(self) -> None:
        bg = build_belief(Board(size=7), {"belief": {}}, probe=None)
        apply_hint(bg, "I think he is near Times Square", "New York", 7, 0.25)

        after_peak = bg.most_likely()
        assert after_peak in [(3, 3), (3, 4), (4, 3)]

    def test_hint_reliability_scales_shift(self) -> None:
        """Higher reliability => larger shift."""
        bg_low = build_belief(
            Board(size=7),
            {"belief": {"hint_reliability": 0.01}},
            probe=None,
        )
        bg_high = build_belief(
            Board(size=7),
            {"belief": {"hint_reliability": 0.5}},
            probe=None,
        )

        apply_hint(bg_low, "near Times Square", "New York", 7, 0.01)
        apply_hint(bg_high, "near Times Square", "New York", 7, 0.5)

        assert bg_high.peak_probability() > bg_low.peak_probability()

    def test_neutral_hint_no_change(self) -> None:
        bg = build_belief(Board(size=7), {"belief": {}}, probe=None)
        before = bg.as_matrix()
        apply_hint(bg, "blah blah blah", "New York", 7, 0.25)
        after = bg.as_matrix()
        assert before == after

    def test_empty_hint_no_change(self) -> None:
        bg = build_belief(Board(size=7), {"belief": {}}, probe=None)
        before = bg.as_matrix()
        apply_hint(bg, "", "New York", 7, 0.25)
        after = bg.as_matrix()
        assert before == after

    def test_sum_remains_one(self) -> None:
        bg = build_belief(Board(size=7), {"belief": {}}, probe=None)
        apply_hint(bg, "near Times Square", "New York", 7, 0.25)
        total = sum(sum(row) for row in bg._matrix)
        assert total == pytest.approx(1.0)


class TestLandmarkTableSync:
    """TC-B11: landmark table structure is correct (sync check placeholder)."""

    def test_new_york_landmarks_present(self) -> None:
        assert "New York" in LANDMARK_CELLS
        for name in ["The Bronx", "Central Park", "Manhattan", "Times Square", "Brooklyn"]:
            assert name in LANDMARK_CELLS["New York"]

    def test_generic_fallback_present(self) -> None:
        for word in ["north", "south", "east", "west", "center"]:
            assert word in GENERIC_FALLBACK

    def test_cells_are_tuples(self) -> None:
        for _arena, landmarks in LANDMARK_CELLS.items():
            for _name, cells in landmarks.items():
                for cell in cells:
                    assert isinstance(cell, tuple)
                    assert len(cell) == 2

    def test_generic_cells_are_tuples(self) -> None:
        for _word, cells in GENERIC_FALLBACK.items():
            for cell in cells:
                assert isinstance(cell, tuple)
                assert len(cell) == 2
