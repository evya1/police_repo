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
    diversity_bonus: int = 0


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
        # Scores are derived ONLY from the verified outcome via the fixed table.
        # Caller-supplied police_score/thief_score are NEVER trusted — the outcome
        # is the single source of truth (negative-probe fix: tamper rows with
        # injected police_score=10 must still score 0/0, not 62/62).
        p_score = calculate_subgame_score(outcome=outcome, role="police")
        t_score = calculate_subgame_score(outcome=outcome, role="thief")

        police_total += p_score
        thief_total += t_score

        scores_detail.append({
            "sub_game_index": idx + 1,  # 1..6, not 0..5
            "outcome": outcome,
            "police_score": p_score,
            "thief_score": t_score,
        })

    tie_applied = False
    diversity_applied = False
    diversity_bonus = 0
    winner = None

    if police_total == thief_total and police_total > 0:
        # Tie +2/+2 only for legitimate equal scores, never for all-sanction 0/0
        # (zeroed rows are sanctions, never tie rows — OPEN-008 interop profile)
        tie_applied = True
        police_total += TIE_SCORE
        thief_total += TIE_SCORE
        winner = None
    elif police_total > thief_total:
        winner = "police"
        if is_new_opponent:
            diversity_bonus = DIVERSITY_REWARD
            diversity_applied = True
    else:
        winner = "thief"
        if is_new_opponent:
            diversity_bonus = DIVERSITY_REWARD
            diversity_applied = True

    return SeriesScoreResult(
        total_police_score=police_total,
        total_thief_score=thief_total,
        tie_applied=tie_applied,
        diversity_applied=diversity_applied,
        diversity_bonus=diversity_bonus,
        winner=winner,
        sub_game_scores=scores_detail,
    )
