from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from police_peer.league.scoring import SeriesScoreResult, calculate_series_scores

NUM_SUBGAMES = 6


class SeriesError(Exception):
    """Raised for series scheduling and integrity violations."""


@dataclass
class SubGameOutcome:
    sub_game_index: int
    game_id: str
    role_for_this_sub_game: str
    outcome: str
    git_commit: str
    tokens_used: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub_game_index": self.sub_game_index,
            "game_id": self.game_id,
            "role": self.role_for_this_sub_game,
            "outcome": self.outcome,
            "git_commit": self.git_commit,
            "tokens_used": self.tokens_used,
        }


def generate_role_schedule(starter_role: str = "police") -> list[str]:
    """Return the alternating 6-subgame role schedule."""
    starter = starter_role.strip().lower()
    if starter not in ("police", "thief"):
        raise SeriesError(f"Invalid starter role '{starter_role}'; must be 'police' or 'thief'")
    other = "thief" if starter == "police" else "police"
    return [starter if i % 2 == 0 else other for i in range(NUM_SUBGAMES)]


class SeriesAggregator:
    """Aggregates verified sub-game results into complete series scoring and evidence."""

    def __init__(self, game_uid: str, is_new_opponent: bool = False) -> None:
        self.game_uid = game_uid
        self.is_new_opponent = is_new_opponent
        self._sub_games: dict[int, SubGameOutcome] = {}

    def record_sub_game(self, outcome: SubGameOutcome) -> None:
        idx = outcome.sub_game_index
        if not (0 <= idx < NUM_SUBGAMES):
            raise SeriesError(f"Sub-game index {idx} out of bounds (0..5)")
        if idx in self._sub_games:
            raise SeriesError(f"Sub-game {idx} already recorded")
        if not outcome.git_commit:
            raise SeriesError(f"Sub-game {idx} missing git_commit hash")
        self._sub_games[idx] = outcome

    def is_complete(self) -> bool:
        return len(self._sub_games) == NUM_SUBGAMES

    def finalize_series(self) -> tuple[SeriesScoreResult, dict[str, Any]]:
        """Finalize series, returning computed scores and artifact payload inputs."""
        if not self.is_complete():
            raise SeriesError(
                f"Cannot finalize series: only {len(self._sub_games)}/{NUM_SUBGAMES} sub-games recorded"
            )

        ordered_sgs = [self._sub_games[i] for i in range(NUM_SUBGAMES)]
        scoring_inputs = [{"outcome": sg.outcome} for sg in ordered_sgs]
        score_res = calculate_series_scores(scoring_inputs, is_new_opponent=self.is_new_opponent)

        git_commits = {sg.game_id: sg.git_commit for sg in ordered_sgs}
        token_totals_per_subgame = {sg.game_id: sg.tokens_used for sg in ordered_sgs}
        total_tokens = sum(token_totals_per_subgame.values())

        artifact_evidence = {
            "game_uid": self.game_uid,
            "sub_game_results": [sg.to_dict() for sg in ordered_sgs],
            "total_police_score": score_res.total_police_score,
            "total_thief_score": score_res.total_thief_score,
            "tie_applied": score_res.tie_applied,
            "total_llm_tokens_per_series": total_tokens,
            "sub_game_git_commits": git_commits,
            "total_llm_tokens_per_sub_game": token_totals_per_subgame,
        }

        return score_res, artifact_evidence
