"""Tests for refusal codes and diagnostics.

SPAR-N00 through SPAR-N10 cover the negotiation surface.
"""

from __future__ import annotations

import pytest

from common.transport.refusals import (
    REFUSAL_CODES,
    Refused,
    diagnostic,
    is_refusal,
    refuse,
)


class TestRefusalCodes:
    """REFUSAL_CODES must contain exactly the negotiation surface codes."""

    def test_contains_expected_codes(self) -> None:
        expected = {
            "SPAR-N00", "SPAR-N01", "SPAR-N02", "SPAR-N03", "SPAR-N04",
            "SPAR-N05", "SPAR-N06", "SPAR-N07", "SPAR-N08", "SPAR-N09",
            "SPAR-N10", "SPAR-N11", "SPAR-N12", "SPAR-N13",
        }
        assert expected == REFUSAL_CODES

    def test_is_frozenset(self) -> None:
        assert isinstance(REFUSAL_CODES, frozenset)

    def test_has_fourteen_codes(self) -> None:
        assert len(REFUSAL_CODES) == 14


class TestRefused:
    """Tests for the Refused exception."""

    def test_inherits_from_exception(self) -> None:
        assert issubclass(Refused, Exception)

    def test_stores_code_and_message(self) -> None:
        exc = Refused("SPAR-N03", "terms differ")
        assert exc.code == "SPAR-N03"
        assert exc.message == "terms differ"

    def test_string_representation(self) -> None:
        exc = Refused("SPAR-N04", "bad sig")
        assert str(exc) == "SPAR-N04: bad sig"

    def test_rejects_unknown_code(self) -> None:
        with pytest.raises(ValueError, match="unknown refusal code"):
            Refused("SPAR-XX", "unknown")


class TestRefuse:
    """Tests for refuse — builds a control-message refusal."""

    def test_returns_dict_with_kind(self) -> None:
        msg = refuse("SPAR-N03", "terms differ")
        assert msg["kind"] == "refusal"
        assert msg["code"] == "SPAR-N03"
        assert msg["detail"] == "terms differ"

    def test_detail_optional(self) -> None:
        msg = refuse("SPAR-N00")
        assert msg["detail"] == ""

    def test_all_codes_valid(self) -> None:
        for code in REFUSAL_CODES:
            msg = refuse(code)
            assert msg["kind"] == "refusal"
            assert msg["code"] == code


class TestIsRefusal:
    """Tests for is_refusal."""

    def test_known_codes_return_true(self) -> None:
        for code in REFUSAL_CODES:
            assert is_refusal(code) is True

    def test_unknown_code_returns_false(self) -> None:
        assert is_refusal("SPAR-XX") is False
        assert is_refusal("") is False
        assert is_refusal("terms") is False


class TestDiagnostic:
    """Tests for diagnostic — human-readable refusal descriptions."""

    def test_returns_string(self) -> None:
        assert isinstance(diagnostic("SPAR-N00"), str)

    def test_known_code_has_diagnostic(self) -> None:
        for code in REFUSAL_CODES:
            diag = diagnostic(code)
            assert isinstance(diag, str)
            assert len(diag) > 0

    def test_unknown_code_returns_fallback(self) -> None:
        diag = diagnostic("SPAR-XX")
        assert "unknown" in diag.lower()

    def test_n00_diagnostic(self) -> None:
        assert "dict" in diagnostic("SPAR-N00").lower()

    def test_n01_diagnostic(self) -> None:
        assert "terms" in diagnostic("SPAR-N01").lower()

    def test_n03_diagnostic(self) -> None:
        assert "constitution" in diagnostic("SPAR-N03").lower()

    def test_n04_diagnostic(self) -> None:
        assert "signature" in diagnostic("SPAR-N04").lower()

    def test_n05_diagnostic(self) -> None:
        assert "locked-model" in diagnostic("SPAR-N05").lower()

    def test_n06_diagnostic(self) -> None:
        assert "sub-game" in diagnostic("SPAR-N06").lower()

    def test_n07_diagnostic(self) -> None:
        assert "role" in diagnostic("SPAR-N07").lower()

    def test_n08_diagnostic(self) -> None:
        assert "group_id" in diagnostic("SPAR-N08").lower()

    def test_n10_diagnostic(self) -> None:
        assert "uid" in diagnostic("SPAR-N10").lower()
