from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Authoritative scoring constants (GAME-013, LEAGUE-005, LEAGUE-006)
CAPTURE_COP = 20
CAPTURE_THIEF = 5
SURVIVAL_COP = 5
SURVIVAL_THIEF = 10
TIE_SCORE = 2
TECHNICAL_LOSS = 0
DIVERSITY_REWARD = 10


class ScoringError(Exception):
    """Raised for invalid game outcomes or role definitions."""


def calculate_subgame_score(*, outcome: str, role: str) -> int:
    """Calculate the score for a single sub-game given outcome and player role."""
    norm_outcome = outcome.strip().lower()
    norm_role = role.strip().lower()

    if norm_outcome in ("technical_loss", "tamper", "disqualification", "forfeit"):
        return TECHNICAL_LOSS

    if norm_outcome == "capture":
        if norm_role in ("police", "cop"):
            return CAPTURE_COP
        if norm_role == "thief":
            return CAPTURE_THIEF
        raise ScoringError(f"Unknown role for capture outcome: {role}")

    if norm_outcome == "survival":
        if norm_role in ("police", "cop"):
            return SURVIVAL_COP
        if norm_role == "thief":
            return SURVIVAL_THIEF
        raise ScoringError(f"Unknown role for survival outcome: {role}")

    raise ScoringError(f"Unrecognized sub-game outcome: {outcome}")


@dataclass
class SeriesScoreResult:
    total_police_score: int
    total_thief_score: int
    tie_applied: bool
    diversity_applied: bool
    winner: str | None
    sub_game_scores: list[dict[str, Any]]


def calculate_series_scores(
    sub_games: list[dict[str, Any]],
    *,
    is_new_opponent: bool = False,
) -> SeriesScoreResult:
    """Aggregate scores across exactly 6 sub-games, applying tie and diversity rules."""
    if len(sub_games) != 6:
        raise ScoringError(f"Counted series must contain exactly 6 sub-games, got {len(sub_games)}")

    police_total = 0
    thief_total = 0
    scores_detail = []

    for idx, sg in enumerate(sub_games):
        outcome = sg.get("outcome", "")
        p_score = sg.get("police_score")
        if p_score is None:
            p_score = calculate_subgame_score(outcome=outcome, role="police")

        t_score = sg.get("thief_score")
        if t_score is None:
            t_score = calculate_subgame_score(outcome=outcome, role="thief")

        police_total += p_score
        thief_total += t_score

        scores_detail.append({
            "sub_game_index": idx,
            "outcome": outcome,
            "police_score": p_score,
            "thief_score": t_score,
        })

    tie_applied = False
    diversity_applied = False
    winner = None

    if police_total == thief_total:
        tie_applied = True
        police_total += TIE_SCORE
        thief_total += TIE_SCORE
        winner = None
    elif police_total > thief_total:
        winner = "police"
        if is_new_opponent:
            police_total += DIVERSITY_REWARD
            diversity_applied = True
    else:
        winner = "thief"
        if is_new_opponent:
            thief_total += DIVERSITY_REWARD
            diversity_applied = True

    return SeriesScoreResult(
        total_police_score=police_total,
        total_thief_score=thief_total,
        tie_applied=tie_applied,
        diversity_applied=diversity_applied,
        winner=winner,
        sub_game_scores=scores_detail,
    )
