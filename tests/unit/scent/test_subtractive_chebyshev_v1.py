"""Conformance tests for subtractive_chebyshev_v1 against pheromone.json.

Covers T005 L78: every emit and decay case in the fixture must reproduce exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from police_peer.scent.profiles.subtractive_chebyshev_v1 import (
    smell_decay,
    smell_emit,
)

FIXTURE = Path(__file__).parent / "fixtures" / "pheromone.json"


@pytest.fixture()
def fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestEmit:
    """Every emit case in pheromone.json."""

    def test_centre_full_field(self, fixture: dict) -> None:
        case = fixture["emit"][0]
        assert case["note"] == "full 5x5 field, centre 0.9, falloff 0.3/step"
        result = smell_emit(
            case["center"],
            case["intensity"],
            case["grid_size"],
            case["board_size"],
        )
        assert result == case["field"]

    def test_corner_clipped(self, fixture: dict) -> None:
        case = fixture["emit"][1]
        assert case["note"] == "corner emission clipped to board bounds"
        result = smell_emit(
            case["center"],
            case["intensity"],
            case["grid_size"],
            case["board_size"],
        )
        assert result == case["field"]


class TestDecay:
    """Every decay case in pheromone.json."""

    def test_one_step_decay(self, fixture: dict) -> None:
        case = fixture["decay"][0]
        assert case["note"] == "one step of decay by 0.1"
        result = smell_decay(case["before"], case["decay"])
        assert result == case["after"]

    def test_floor_clamp(self, fixture: dict) -> None:
        case = fixture["decay"][1]
        assert case["note"] == "clamps to 0.0 at the floor"
        result = smell_decay(case["before"], case["decay"])
        assert result == case["after"]


class TestNoForgedScent:
    """M-01 STRAT-004: emission never occurs outside the 5x5 window around center."""

    def test_emission_within_chebyshev_2(self) -> None:
        """After full_turn(center), every changed cell is within Chebyshev distance 2."""
        from police_peer.scent.model import make_trail

        trail = make_trail(board_size=7, model="subtractive_chebyshev_v1")
        center = (3, 3)
        result = trail.full_turn(center)
        for key in result:
            r, c = map(int, key.split(","))
            assert max(abs(r - center[0]), abs(c - center[1])) <= 2

    def test_emission_only_at_center(self) -> None:
        """Emission is centered on the emitting cell; no other cells receive a deposit."""
        from police_peer.scent.model import make_trail

        trail = make_trail(board_size=7, model="subtractive_chebyshev_v1")
        center = (3, 3)
        result = trail.full_turn(center)
        # All keys must be within the 5x5 window centered at (3,3)
        for key in result:
            r, c = map(int, key.split(","))
            assert 1 <= r <= 5
            assert 1 <= c <= 5


class TestEdges:
    """Corner emissions and out-of-board clipping are deterministic and board-bounded."""

    def test_corner_emission_board_bounded(self) -> None:
        from police_peer.scent.model import make_trail

        trail = make_trail(board_size=7, model="subtractive_chebyshev_v1")
        center = (0, 0)
        result = trail.full_turn(center)
        for key in result:
            r, c = map(int, key.split(","))
            assert 0 <= r < 7
            assert 0 <= c < 7
        # full_turn does emit-then-decay, so subtract 0.1 from each emit value
        expected = {
            "0,0": 0.8, "0,1": 0.5, "0,2": 0.2,
            "1,0": 0.5, "1,1": 0.5, "1,2": 0.2,
            "2,0": 0.2, "2,1": 0.2, "2,2": 0.2,
        }
        assert result == expected
