"""General tests for validate_turn covering all fields.

FR-25: validate before any state change.
"""

from __future__ import annotations

import pytest

from common.transport.validators import validate_turn


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


class TestValidateTurnGeneral:
    """General tests for validate_turn covering all fields."""

    def test_valid_turn_accepted(self) -> None:
        result = validate_turn(_valid_turn(), board_size=7)
        assert result == "accept"

    def test_missing_step_refused(self) -> None:
        data = _valid_turn()
        del data["step"]
        result = validate_turn(data, board_size=7)
        assert "step" in result

    def test_bool_step_refused(self) -> None:
        result = validate_turn(_valid_turn(step=True), board_size=7)
        assert "step" in result

    def test_negative_step_refused(self) -> None:
        result = validate_turn(_valid_turn(step=-1), board_size=7)
        assert "step" in result

    def test_missing_sender_refused(self) -> None:
        data = _valid_turn()
        del data["sender"]
        result = validate_turn(data, board_size=7)
        assert "sender" in result

    def test_empty_sender_refused(self) -> None:
        result = validate_turn(_valid_turn(sender=""), board_size=7)
        assert "sender" in result

    def test_missing_commit_refused(self) -> None:
        data = _valid_turn()
        del data["commit"]
        result = validate_turn(data, board_size=7)
        assert "commit" in result

    def test_short_commit_refused(self) -> None:
        result = validate_turn(_valid_turn(commit="abc"), board_size=7)
        assert "commit" in result

    def test_optional_none_accepted(self) -> None:
        result = validate_turn(_valid_turn(barrier_placed=None, capture_claim=None), board_size=7)
        assert result == "accept"

    def test_multiple_problems_reported(self) -> None:
        result = validate_turn(_valid_turn(step="bad", sender="", commit="short"), board_size=7)
        assert "step" in result
        assert "sender" in result
        assert "commit" in result


_OUT_OF_BOUNDS = [[99, 99], [-1, -1], [0, 7], [7, 0]]


class TestHostileOptionalFields:
    """HIGH-2: hostile optional turn data is a verdict, never a crash and never a mutation."""

    @pytest.mark.parametrize("cell", _OUT_OF_BOUNDS)
    @pytest.mark.parametrize("field", ["barrier_placed", "capture_claim"])
    def test_out_of_bounds_cell_refused(self, field: str, cell: list[int]) -> None:
        result = validate_turn(_valid_turn(**{field: cell}), board_size=7)
        assert field in result
        assert "out of bounds" in result

    @pytest.mark.parametrize("field", ["barrier_placed", "capture_claim"])
    @pytest.mark.parametrize("bad", ["nope", 3, [1], [1, 2, 3], [1, "2"], [True, False], {"r": 1}])
    def test_malformed_cell_refused(self, field: str, bad: object) -> None:
        assert field in validate_turn(_valid_turn(**{field: bad}), board_size=7)

    @pytest.mark.parametrize("field", ["barrier_placed", "capture_claim"])
    @pytest.mark.parametrize("cell", [[0, 0], [6, 6]])
    def test_boundary_cells_accepted(self, field: str, cell: list[int]) -> None:
        assert validate_turn(_valid_turn(**{field: cell}), board_size=7) == "accept"

    def test_board_size_is_negotiated_not_fixed_at_seven(self) -> None:
        turn = _valid_turn(capture_claim=[8, 8])
        assert validate_turn(turn, board_size=7) != "accept"
        assert validate_turn(turn, board_size=9) == "accept"

    @pytest.mark.parametrize("bad", ["nope", [1, 2], 7, True, {"caught": True},
                                     {"claim": [1, 2]}, {"claim": [9, 9], "caught": True},
                                     {"claim": [1, 2], "caught": "yes"}])
    def test_malformed_claim_response_refused(self, bad: object) -> None:
        assert "claim_response" in validate_turn(_valid_turn(claim_response=bad), board_size=7)

    @pytest.mark.parametrize("caught", [True, False])
    def test_well_formed_claim_response_accepted(self, caught: bool) -> None:
        answer = {"claim": [3, 3], "caught": caught}
        assert validate_turn(_valid_turn(claim_response=answer), board_size=7) == "accept"

    @pytest.mark.parametrize("bad", ["nope", 7, [1, 2], True, {}, {"type": "victory"},
                                     {"type": None}, {"type": ["capture"]}])
    def test_malformed_win_claim_refused(self, bad: object) -> None:
        assert "win_claim" in validate_turn(_valid_turn(win_claim=bad), board_size=7)

    @pytest.mark.parametrize("kind", ["capture", "survival"])
    def test_supported_win_claim_accepted(self, kind: str) -> None:
        assert validate_turn(_valid_turn(win_claim={"type": kind}), board_size=7) == "accept"

    @pytest.mark.parametrize("message", [None, [], "turn", 7, ["step", 1], object()])
    def test_non_mapping_message_is_a_verdict_not_a_crash(self, message: object) -> None:
        result = validate_turn(message, board_size=7)
        assert result != "accept"
        assert result.startswith("message: required mapping")

    @pytest.mark.parametrize("sender", ["referee", "POLICE", "", None, 1, ["thief"]])
    def test_invalid_sender_refused(self, sender: object) -> None:
        assert "sender" in validate_turn(_valid_turn(sender=sender), board_size=7)

    @pytest.mark.parametrize("sender", ["police", "thief"])
    def test_protocol_senders_accepted(self, sender: str) -> None:
        assert validate_turn(_valid_turn(sender=sender), board_size=7) == "accept"

    def test_extension_field_carrying_a_coordinate_is_refused(self) -> None:
        result = validate_turn(_valid_turn(shadow_position=[1, 2]), board_size=7)
        assert "position leak" in result

    def test_extension_field_carrying_a_bare_number_is_refused(self) -> None:
        assert "position leak" in validate_turn(_valid_turn(row=3), board_size=7)

    def test_non_position_extension_still_tolerated(self) -> None:
        turn = _valid_turn(engine_note="chasing", tags=["a", "b", "c"])
        assert validate_turn(turn, board_size=7) == "accept"

    @pytest.mark.parametrize("bad_size", [0, -1, 7.0, "7", True, None])
    def test_invalid_board_size_is_a_programmer_error(self, bad_size: object) -> None:
        with pytest.raises(ValueError, match="board_size must be a positive int"):
            validate_turn(_valid_turn(), board_size=bad_size)
