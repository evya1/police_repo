import pytest

from police_peer.league.scoring import (
    CAPTURE_COP,
    CAPTURE_THIEF,
    DIVERSITY_REWARD,
    SURVIVAL_COP,
    SURVIVAL_THIEF,
    TIE_SCORE,
    ScoringError,
    calculate_series_scores,
    calculate_subgame_score,
)


def test_calculate_subgame_score():
    assert calculate_subgame_score(outcome="capture", role="police") == CAPTURE_COP
    assert calculate_subgame_score(outcome="capture", role="thief") == CAPTURE_THIEF
    assert calculate_subgame_score(outcome="survival", role="police") == SURVIVAL_COP
    assert calculate_subgame_score(outcome="survival", role="thief") == SURVIVAL_THIEF
    assert calculate_subgame_score(outcome="technical_loss", role="police") == 0
    assert calculate_subgame_score(outcome="tamper", role="thief") == 0

    with pytest.raises(ScoringError):
        calculate_subgame_score(outcome="invalid_outcome", role="police")


def test_calculate_series_scores_six_games_required():
    with pytest.raises(ScoringError, match="exactly 6"):
        calculate_series_scores([{"outcome": "capture"}] * 5)


def test_calculate_series_scores_police_win_with_diversity():
    # 4 captures (cop=20, thief=5), 2 survivals (cop=5, thief=10)
    games = [{"outcome": "capture"}] * 4 + [{"outcome": "survival"}] * 2
    # Base: Police = 4*20 + 2*5 = 90. Thief = 4*5 + 2*10 = 40.
    res = calculate_series_scores(games, is_new_opponent=True)
    assert res.winner == "police"
    # Diversity bonus is tracked separately, NOT baked into the total (T019 fix)
    assert res.total_police_score == 90
    assert res.total_thief_score == 40
    assert res.tie_applied is False
    assert res.diversity_applied is True
    assert res.diversity_bonus == DIVERSITY_REWARD


def test_calculate_series_scores_tie():
    # Real tie: 1 capture (20/5) + 3 survivals (15/30) + 2 technical_loss (0/0)
    # Police = 20+15+0 = 35. Thief = 5+30+0 = 35. Both > 0, so tie +2/+2.
    games = (
        [{"outcome": "capture"}] * 1
        + [{"outcome": "survival"}] * 3
        + [{"outcome": "technical_loss"}] * 2
    )
    res = calculate_series_scores(games, is_new_opponent=False)
    assert res.winner is None
    assert res.tie_applied is True
    assert res.total_police_score == 35 + TIE_SCORE
    assert res.total_thief_score == 35 + TIE_SCORE


def test_tamper_rows_score_zero_not_62():
    """Negative-probe fix: 6 tamper rows with injected police_score=10/thief_score=10
    MUST score 0/0, NOT 62/62. Caller-supplied scores are IGNORED."""
    games = [
        {"outcome": "tamper", "police_score": 10, "thief_score": 10}
        for _ in range(6)
    ]
    res = calculate_series_scores(games, is_new_opponent=False)
    assert res.total_police_score == 0
    assert res.total_thief_score == 0
    assert res.tie_applied is False  # 0/0 is sanctions, not a tie


def test_caller_supplied_scores_ignored():
    """Caller-supplied police_score/thief_score must NEVER override the outcome table."""
    games_capture = [{"outcome": "capture", "police_score": 999, "thief_score": 999}] * 6
    res = calculate_series_scores(games_capture, is_new_opponent=False)
    # Should be 6*20=120 for police, 6*5=30 for thief, NOT 999*6
    assert res.total_police_score == 120
    assert res.total_thief_score == 30


def test_sub_game_indices_are_1_based():
    """Sub-game indices must be 1..6, not 0..5 (T019 fix)."""
    games = [{"outcome": "capture"}] * 6
    res = calculate_series_scores(games, is_new_opponent=False)
    indices = [s["sub_game_index"] for s in res.sub_game_scores]
    assert indices == [1, 2, 3, 4, 5, 6]
