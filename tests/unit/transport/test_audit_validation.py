"""Tests for validate_audit — all required fields and edge cases.

FR-25: validate before any state change.
"""

from __future__ import annotations

from common.transport.validators import validate_audit


def _valid_audit(**overrides: object) -> dict:
    base: dict = {
        "sender": "thief",
        "records": [{"state": "start", "move": "north", "intent": "evade", "nonce": "x"}],
        "result_claim": "survival",
    }
    base.update(overrides)
    return base


class TestValidateAuditGeneral:
    """General tests for validate_audit."""

    def test_valid_audit_accepted(self) -> None:
        result = validate_audit(_valid_audit())
        assert result == "accept"

    def test_missing_sender_refused(self) -> None:
        data = _valid_audit()
        del data["sender"]
        result = validate_audit(data)
        assert "sender" in result

    def test_empty_sender_refused(self) -> None:
        result = validate_audit(_valid_audit(sender=""))
        assert "sender" in result

    def test_missing_records_refused(self) -> None:
        data = _valid_audit()
        del data["records"]
        result = validate_audit(data)
        assert "records" in result

    def test_string_records_refused(self) -> None:
        result = validate_audit(_valid_audit(records="not a list"))
        assert "records" in result

    def test_empty_records_accepted(self) -> None:
        # An empty record list is valid for a game that ended before any moves.
        result = validate_audit(_valid_audit(records=[]))
        assert result == "accept"

    def test_missing_result_claim_refused(self) -> None:
        data = _valid_audit()
        del data["result_claim"]
        result = validate_audit(data)
        assert "result_claim" in result

    def test_empty_result_claim_refused(self) -> None:
        result = validate_audit(_valid_audit(result_claim=""))
        assert "result_claim" in result

    def test_valid_claims_accepted(self) -> None:
        for claim in ("capture", "survival", "timeout"):
            result = validate_audit(_valid_audit(result_claim=claim))
            assert result == "accept"

    def test_multiple_problems_reported(self) -> None:
        result = validate_audit(_valid_audit(sender="", records="bad", result_claim=""))
        assert "sender" in result
        assert "records" in result
        assert "result_claim" in result
