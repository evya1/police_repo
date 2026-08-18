"""General tests for validate_turn covering all fields.

FR-25: validate before any state change.
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


class TestValidateTurnGeneral:
    """General tests for validate_turn covering all fields."""

    def test_valid_turn_accepted(self) -> None:
        result = validate_turn(_valid_turn())
        assert result == "accept"

    def test_missing_step_refused(self) -> None:
        data = _valid_turn()
        del data["step"]
        result = validate_turn(data)
        assert "step" in result

    def test_bool_step_refused(self) -> None:
        result = validate_turn(_valid_turn(step=True))
        assert "step" in result

    def test_negative_step_refused(self) -> None:
        result = validate_turn(_valid_turn(step=-1))
        assert "step" in result

    def test_missing_sender_refused(self) -> None:
        data = _valid_turn()
        del data["sender"]
        result = validate_turn(data)
        assert "sender" in result

    def test_empty_sender_refused(self) -> None:
        result = validate_turn(_valid_turn(sender=""))
        assert "sender" in result

    def test_missing_commit_refused(self) -> None:
        data = _valid_turn()
        del data["commit"]
        result = validate_turn(data)
        assert "commit" in result

    def test_short_commit_refused(self) -> None:
        result = validate_turn(_valid_turn(commit="abc"))
        assert "commit" in result

    def test_optional_none_accepted(self) -> None:
        result = validate_turn(_valid_turn(barrier_placed=None, capture_claim=None))
        assert result == "accept"

    def test_multiple_problems_reported(self) -> None:
        result = validate_turn(_valid_turn(step="bad", sender="", commit="short"))
        assert "step" in result
        assert "sender" in result
        assert "commit" in result
