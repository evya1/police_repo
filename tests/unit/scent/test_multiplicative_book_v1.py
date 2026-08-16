"""Conformance tests for multiplicative_book_v1 against scent_book_v3.json.

Covers T005 L79: every case in the fixture must reproduce exactly, zero tolerance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from police_peer.scent.profiles.multiplicative_book_v1 import (
    BOOK_KERNEL,
    book_full_turn,
    book_kernel_delta,
    book_update,
)

FIXTURE = Path(__file__).parent / "fixtures" / "scent_book_v3.json"


@pytest.fixture()
def fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestBookKernel:
    """The kernel is the printed 5x5 table, verbatim."""

    def test_kernel_values(self) -> None:
        expected = (
            (0.04, 0.14, 0.20, 0.14, 0.04),
            (0.14, 0.42, 0.62, 0.42, 0.14),
            (0.20, 0.62, 0.90, 0.62, 0.20),
            (0.14, 0.42, 0.62, 0.42, 0.14),
            (0.04, 0.14, 0.20, 0.14, 0.04),
        )
        assert expected == BOOK_KERNEL

    def test_kernel_delta_center(self) -> None:
        assert book_kernel_delta(0, 0) == 0.90

    def test_kernel_delta_orth(self) -> None:
        assert book_kernel_delta(0, 1) == 0.62
        assert book_kernel_delta(1, 0) == 0.62

    def test_kernel_delta_next_orth(self) -> None:
        assert book_kernel_delta(0, 2) == 0.20
        assert book_kernel_delta(2, 0) == 0.20

    def test_kernel_delta_diag(self) -> None:
        assert book_kernel_delta(1, 1) == 0.42

    def test_kernel_delta_corner(self) -> None:
        assert book_kernel_delta(2, 2) == 0.04

    def test_kernel_delta_out_of_bounds(self) -> None:
        assert book_kernel_delta(3, 0) == 0.0
        assert book_kernel_delta(0, 3) == 0.0
        assert book_kernel_delta(-3, 0) == 0.0


class TestBookUpdate:
    """The update formula with pinned evaluation order."""

    def test_pinned_order(self) -> None:
        """(1 - rho) * tau + delta, then clamp — not tau - rho * tau + delta."""
        # The fixture's ordering_probe cases
        cases = [
            (0.05, 0.04, 0.085),
            (0.05, 0.14, 0.18500000000000003),
            (0.1, 0.14, 0.23000000000000004),
        ]
        for tau, delta, expected in cases:
            result = book_update(tau, delta, 0.1, 0.9)
            assert result == expected

    def test_clamp_case(self) -> None:
        """tau=0.9, delta=0.62 → raw 1.4300000000000002, clamped to 0.9."""
        result = book_update(0.9, 0.62, 0.1, 0.9)
        assert result == 0.9
        # Verify the raw intermediate value
        raw = (1 - 0.1) * 0.9 + 0.62
        assert raw == 1.4300000000000002

    def test_pure_decay(self) -> None:
        """tau=0.9, delta=0 → 0.81."""
        result = book_update(0.9, 0.0, 0.1, 0.9)
        assert result == 0.81


class TestBookFullTurn:
    """Every emit and field-walk case in scent_book_v3.json."""

    def test_emit_empty_field_center(self, fixture: dict) -> None:
        case = fixture["emit"][0]
        assert case["note"] == "kernel deposited on an empty field, board centre"
        result = book_full_turn({}, case["center"], 0.1, 0.9, 7)
        assert result == case["field"]

    def test_emit_corner_clipped(self, fixture: dict) -> None:
        case = fixture["emit"][1]
        assert case["note"] == "corner emission clipped to board bounds"
        result = book_full_turn({}, case["center"], 0.1, 0.9, 7)
        assert result == case["field"]

    def test_scalar_pure_decay(self, fixture: dict) -> None:
        case = fixture["scalar_traces"]["pure_decay"]
        result = book_update(case["tau"], case["delta"], 0.1, 0.9)
        assert result == case["after"]

    def test_scalar_clamp(self, fixture: dict) -> None:
        case = fixture["scalar_traces"]["clamp"]
        result = book_update(case["tau"], case["delta"], 0.1, 0.9)
        assert result == case["after"]

    def test_field_walk_turn_1(self, fixture: dict) -> None:
        turn = fixture["field_walk"]["turns"][0]
        assert turn["turn"] == 1
        result = book_full_turn({}, turn["center"], 0.1, 0.9, 7)
        assert result == turn["field"]

    def test_field_walk_turn_2(self, fixture: dict) -> None:
        turn = fixture["field_walk"]["turns"][1]
        assert turn["turn"] == 2
        prev = fixture["field_walk"]["turns"][0]["field"]
        result = book_full_turn(prev, turn["center"], 0.1, 0.9, 7)
        assert result == turn["field"]

    def test_field_walk_turn_3(self, fixture: dict) -> None:
        turn = fixture["field_walk"]["turns"][2]
        assert turn["turn"] == 3
        prev = fixture["field_walk"]["turns"][1]["field"]
        result = book_full_turn(prev, turn["center"], 0.1, 0.9, 7)
        assert result == turn["field"]


class TestScalarTraces:
    """The chain trace from scent_book_v3.json."""

    def test_chain_steps(self, fixture: dict) -> None:
        chain = fixture["scalar_traces"]["chain"]
        tau = 0.0
        for step in chain["steps"]:
            tau = book_update(tau, step["delta"], 0.1, 0.9)
            assert tau == step["tau"]
        # Fork case: same predecessor (step 2 tau=0.758) with delta=0.14 instead of 0.2
        tau_fork = book_update(0.758, 0.14, 0.1, 0.9)
        assert tau_fork == 0.8222



