"""Tests for validate_turn — TC-08 through TC-11.

FR-25: validate before any state change.
TC-08: missing smell_grid => refused, zero state change.
TC-09: stringified intensity refused; numeric accepted.
TC-10: uppercase commit refused.
TC-11: empty timestamp refused.
"""

from __future__ import annotations

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


# --- TC-08: missing smell_grid => refused, zero state change --------------------------------


class TestTc08MissingSmellGrid:
    """TC-08: turn message missing a required key (smell_grid) is refused with zero state change."""

    def test_missing_smell_grid_refused(self) -> None:
        data = _valid_turn()
        del data["smell_grid"]
        result = validate_turn(data, board_size=7)
        assert result != "accept"
        assert "smell_grid" in result

    def test_none_smell_grid_refused(self) -> None:
        result = validate_turn(_valid_turn(smell_grid=None), board_size=7)
        assert result != "accept"
        assert "smell_grid" in result

    def test_empty_dict_smell_grid_accepted(self) -> None:
        # An empty dict means no smells emitted this turn — legitimate game state.
        result = validate_turn(_valid_turn(smell_grid={}), board_size=7)
        assert result == "accept"


# --- TC-09: stringified intensity refused; numeric accepted ----------------------------------


class TestTc09SmellGridTypes:
    """TC-09: stringified intensity refused; numeric accepted."""

    def test_numeric_intensity_accepted(self) -> None:
        result = validate_turn(_valid_turn(smell_grid={"0,0": 0.5}), board_size=7)
        assert result == "accept"

    def test_int_intensity_accepted(self) -> None:
        result = validate_turn(_valid_turn(smell_grid={"0,0": 1}), board_size=7)
        assert result == "accept"

    def test_stringified_intensity_refused(self) -> None:
        result = validate_turn(_valid_turn(smell_grid={"0,0": "0.5"}), board_size=7)
        assert result != "accept"
        assert "smell_grid" in result

    def test_bool_intensity_refused(self) -> None:
        # bool is a subclass of int in Python; it must be rejected explicitly.
        result = validate_turn(_valid_turn(smell_grid={"0,0": True}), board_size=7)
        assert result != "accept"
        assert "smell_grid" in result


# --- TC-10: uppercase commit refused ---------------------------------------------------------


class TestTc10CommitCase:
    """TC-10: uppercase commit is refused."""

    def test_uppercase_commit_refused(self) -> None:
        result = validate_turn(_valid_turn(commit="A" * 64), board_size=7)
        assert result != "accept"
        assert "commit" in result

    def test_mixed_case_commit_refused(self) -> None:
        result = validate_turn(_valid_turn(commit="a" * 32 + "B" * 32), board_size=7)
        assert result != "accept"
        assert "commit" in result

    def test_lowercase_commit_accepted(self) -> None:
        result = validate_turn(_valid_turn(commit="a" * 64), board_size=7)
        assert result == "accept"


# --- TC-11: empty timestamp refused ----------------------------------------------------------


class TestTc11EmptyTimestamp:
    """TC-11: empty timestamp is refused."""

    def test_empty_timestamp_refused(self) -> None:
        result = validate_turn(_valid_turn(timestamp=""), board_size=7)
        assert result != "accept"
        assert "timestamp" in result

    def test_missing_timestamp_refused(self) -> None:
        data = _valid_turn()
        del data["timestamp"]
        result = validate_turn(data, board_size=7)
        assert result != "accept"
        assert "timestamp" in result

    def test_valid_timestamp_accepted(self) -> None:
        result = validate_turn(_valid_turn(timestamp="2026-01-01T00:00:00Z"), board_size=7)
        assert result == "accept"
