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
    assert res.total_police_score == 90 + DIVERSITY_REWARD
    assert res.total_thief_score == 40
    assert res.tie_applied is False
    assert res.diversity_applied is True


def test_calculate_series_scores_tie():
    # Symmetric 3 captures, 3 survivals
    # Police = 3*20 + 3*5 = 75. Thief = 3*5 + 3*10 = 45 -> not tied.
    # To get tie: need equal total. e.g. custom scores:
    games = [
        {"police_score": 10, "thief_score": 10},
        {"police_score": 10, "thief_score": 10},
        {"police_score": 10, "thief_score": 10},
        {"police_score": 10, "thief_score": 10},
        {"police_score": 10, "thief_score": 10},
        {"police_score": 10, "thief_score": 10},
    ]
    res = calculate_series_scores(games, is_new_opponent=False)
    assert res.winner is None
    assert res.tie_applied is True
    assert res.total_police_score == 60 + TIE_SCORE
    assert res.total_thief_score == 60 + TIE_SCORE
