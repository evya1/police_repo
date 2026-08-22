"""Tests for assert_no_position_leak — TC-13 and edge cases.

FR-26/27: no position leak; hint is text-only (NET-004).
"""

from __future__ import annotations

import pytest

from common.transport.validators import assert_no_position_leak, validate_turn


def _valid_turn(**overrides: object) -> dict:
    base: dict = {
        "step": 1,
        "sender": "thief",
        "hint": "I think they are nearby",
        "smell_grid": {"0,0": 0.5, "1,1": 0.3},
        "commit": "a" * 64,
        "timestamp": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


class TestTc13PositionLeak:
    """TC-13: structural scan of the turn wire shape — no field carries a numeric position
    except the explicitly public barrier_placed/capture_claim; hint is text-only (NET-004, FR-26/27).
    """

    def test_barrier_placed_accepted(self) -> None:
        turn = _valid_turn(barrier_placed=[1, 2])
        assert_no_position_leak(turn)

    def test_capture_claim_accepted(self) -> None:
        turn = _valid_turn(capture_claim=[3, 4])
        assert_no_position_leak(turn)

    def test_hint_string_accepted(self) -> None:
        turn = _valid_turn(hint="1,2,3")
        assert_no_position_leak(turn)

    def test_sender_as_list_refused(self) -> None:
        turn = _valid_turn(sender=[1, 2])
        with pytest.raises(ValueError, match="position leak"):
            assert_no_position_leak(turn)

    def test_unknown_field_with_list_refused(self) -> None:
        turn = _valid_turn()
        turn["my_field"] = [1, 2]
        with pytest.raises(ValueError, match="position leak"):
            assert_no_position_leak(turn)

    def test_random_list_in_hint_field_refused(self) -> None:
        turn = _valid_turn()
        turn["hint"] = [1, 2]
        with pytest.raises(ValueError, match="position leak"):
            assert_no_position_leak(turn)

    def test_empty_hint_accepted(self) -> None:
        turn = _valid_turn(hint="")
        assert_no_position_leak(turn)

    def test_step_not_flagged(self) -> None:
        # step is a counter, not a position — should never raise.
        turn = _valid_turn(step=42)
        assert_no_position_leak(turn)

    def test_smell_grid_values_not_flagged(self) -> None:
        # smell_grid values are intensities, not positions.
        turn = _valid_turn(smell_grid={"0,0": 0.9, "1,1": 0.1})
        assert_no_position_leak(turn)

    def test_commit_not_flagged(self) -> None:
        # commit is a hex string, not numeric.
        turn = _valid_turn(commit="a" * 64)
        assert_no_position_leak(turn)

    def test_optional_fields_accepted(self) -> None:
        turn = _valid_turn(
            barrier_placed=[0, 0],
            capture_claim=[1, 1],
            claim_response={"type": "denied"},
            win_claim=None,
        )
        assert_no_position_leak(turn)


class TestLeakIsRefusedByThePreflight:
    """The leak scan runs INSIDE validate_turn, so the wire preflight refuses it as a verdict."""

    def test_extension_coordinate_becomes_a_verdict_not_an_exception(self) -> None:
        result = validate_turn(_valid_turn(shadow_position=[1, 2]), board_size=7)
        assert "position leak" in result

    def test_declared_position_fields_still_pass_the_preflight(self) -> None:
        turn = _valid_turn(barrier_placed=[0, 0], capture_claim=[1, 1])
        assert validate_turn(turn, board_size=7) == "accept"

    def test_step_and_smell_grid_numerics_still_pass_the_preflight(self) -> None:
        turn = _valid_turn(step=9, smell_grid={"0,0": 0.9, "1,1": 0.1})
        assert validate_turn(turn, board_size=7) == "accept"
