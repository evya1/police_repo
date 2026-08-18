"""Tests for scoring logic.

Covers BL-21, BL-22.
"""

from __future__ import annotations

from police_peer.domain import (
    SCORES,
    TIE_SCORE,
    ZEROED,
    Outcome,
    Role,
    is_tie_row,
    score_for,
    settled_outcome,
)


class TestOutcomeEnum:
    """Outcome values are fixed."""

    def test_outcome_values(self) -> None:
        assert Outcome.CAPTURE.value == "capture"
        assert Outcome.SURVIVAL.value == "survival"
        assert Outcome.TIMEOUT.value == "timeout"
        assert Outcome.TECHNICAL_LOSS.value == "technical_loss"
        assert Outcome.TAMPER_FORFEIT.value == "tamper_forfeit"

    def test_all_outcomes_present(self) -> None:
        """All five outcomes exist."""
        assert len(Outcome) == 5


class TestRoleEnum:
    """Role values and transitions."""

    def test_role_values(self) -> None:
        assert Role.POLICE.value == "police"
        assert Role.THIEF.value == "thief"

    def test_role_other(self) -> None:
        assert Role.POLICE.other == Role.THIEF
        assert Role.THIEF.other == Role.POLICE

    def test_other_is_involution(self) -> None:
        assert Role.POLICE.other.other == Role.POLICE
        assert Role.THIEF.other.other == Role.THIEF


class TestScores:
    """BL-21: fixed scoring table."""

    def test_capture_scores(self) -> None:
        """BL-21: capture gives Police 20 and Thief 5."""
        assert SCORES[Outcome.CAPTURE] == (20, 5)

    def test_survival_scores(self) -> None:
        """BL-21: survival gives Police 5 and Thief 10."""
        assert SCORES[Outcome.SURVIVAL] == (5, 10)

    def test_timeout_scores(self) -> None:
        """Technical loss / timeout zeros both sides."""
        assert SCORES[Outcome.TIMEOUT] == (0, 0)

    def test_technical_loss_scores(self) -> None:
        assert SCORES[Outcome.TECHNICAL_LOSS] == (0, 0)

    def test_tamper_forfeit_scores(self) -> None:
        assert SCORES[Outcome.TAMPER_FORFEIT] == (0, 0)

    def test_scores_are_fixed(self) -> None:
        """Fixed values match the official table."""
        assert SCORES[Outcome.CAPTURE] == (20, 5)
        assert SCORES[Outcome.SURVIVAL] == (5, 10)
        assert SCORES[Outcome.TIMEOUT] == (0, 0)
        assert SCORES[Outcome.TECHNICAL_LOSS] == (0, 0)
        assert SCORES[Outcome.TAMPER_FORFEIT] == (0, 0)


class TestZeroed:
    """BL-22: zeroed outcomes are sanctions, not ties."""

    def test_zeroed_outcomes(self) -> None:
        assert Outcome.TIMEOUT in ZEROED
        assert Outcome.TECHNICAL_LOSS in ZEROED
        assert Outcome.TAMPER_FORFEIT in ZEROED

    def test_played_outcomes_not_zeroed(self) -> None:
        assert Outcome.CAPTURE not in ZEROED
        assert Outcome.SURVIVAL not in ZEROED


class TestScoreFor:
    """BL-21: score_for returns correct score per role."""

    def test_capture_police(self) -> None:
        assert score_for(Outcome.CAPTURE, Role.POLICE) == 20

    def test_capture_thief(self) -> None:
        assert score_for(Outcome.CAPTURE, Role.THIEF) == 5

    def test_survival_police(self) -> None:
        assert score_for(Outcome.SURVIVAL, Role.POLICE) == 5

    def test_survival_thief(self) -> None:
        assert score_for(Outcome.SURVIVAL, Role.THIEF) == 10

    def test_technical_loss_both(self) -> None:
        assert score_for(Outcome.TECHNICAL_LOSS, Role.POLICE) == 0
        assert score_for(Outcome.TECHNICAL_LOSS, Role.THIEF) == 0

    def test_timeout_both(self) -> None:
        assert score_for(Outcome.TIMEOUT, Role.POLICE) == 0
        assert score_for(Outcome.TIMEOUT, Role.THIEF) == 0


class TestIsTieRow:
    """BL-22: tie flag is false for zeroed outcomes."""

    def test_capture_not_tie(self) -> None:
        """Capture with unequal scores is not a tie."""
        assert is_tie_row(Outcome.CAPTURE, 20, 5) is False

    def test_survival_not_tie(self) -> None:
        """Survival with unequal scores is not a tie."""
        assert is_tie_row(Outcome.SURVIVAL, 5, 10) is False

    def test_technical_loss_not_tie(self) -> None:
        """BL-22: technical loss 0-0 is NOT a tie."""
        assert is_tie_row(Outcome.TECHNICAL_LOSS, 0, 0) is False

    def test_timeout_not_tie(self) -> None:
        """BL-22: timeout 0-0 is NOT a tie."""
        assert is_tie_row(Outcome.TIMEOUT, 0, 0) is False

    def test_equal_played_scores_is_tie(self) -> None:
        """Equal scores on a played outcome is a tie."""
        # This would require a custom scoring table; with fixed scores it doesn't happen
        # but the function should correctly identify it
        assert is_tie_row(Outcome.CAPTURE, 20, 20) is True


class TestTieScore:
    """TIE_SCORE is fixed at 2."""

    def test_tie_score_value(self) -> None:
        assert TIE_SCORE == 2


class TestSettledOutcome:
    """Settlement logic."""

    def test_played_outcome_no_audits_not_settled(self) -> None:
        """Played outcome without audits is not settled (unless zeroed)."""
        result, is_settled = settled_outcome(Outcome.CAPTURE, False, False)
        assert result == Outcome.CAPTURE
        assert is_settled is False

    def test_zeroed_outcome_no_audits_settled(self) -> None:
        """Zeroed outcome without audits is settled."""
        result, is_settled = settled_outcome(Outcome.TECHNICAL_LOSS, False, False)
        assert result == Outcome.TECHNICAL_LOSS
        assert is_settled is True

    def test_audits_clean(self) -> None:
        """Audits present and passed → outcome stands, settled."""
        result, is_settled = settled_outcome(Outcome.CAPTURE, True, True)
        assert result == Outcome.CAPTURE
        assert is_settled is True

    def test_audits_failed(self) -> None:
        """Audits present but failed → TAMPER_FORFEIT, settled."""
        result, is_settled = settled_outcome(Outcome.CAPTURE, True, False)
        assert result == Outcome.TAMPER_FORFEIT
        assert is_settled is True
