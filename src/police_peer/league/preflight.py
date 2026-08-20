from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MIN_COUNTED_MATCHES = 2
MAX_COUNTED_MATCHES = 10
MAX_MATCHES_PER_OPPONENT = 1


class LeagueEligibilityError(Exception):
    """Base exception for league pairing and eligibility guard violations."""


class MaxMatchesExceededError(LeagueEligibilityError):
    """Raised when an eleventh counted match is attempted."""


class DuplicateOpponentError(LeagueEligibilityError):
    """Raised when a second counted match with the same opponent is attempted."""


class FalseDeclarationError(LeagueEligibilityError):
    """Raised when declared prior match count does not match true record."""


class InvalidModeError(LeagueEligibilityError):
    """Raised when match mode is not 'counted' or 'warmup'."""


@dataclass
class PriorMatchRecord:
    game_uid: str
    opponent_team: str
    mode: str = "counted"
    timestamp: str = ""
    signature: str = ""
    extra_evidence: dict[str, Any] = field(default_factory=dict)


class LeaguePairingGuard:
    """Enforces LEAGUE-002..007 pairing eligibility, opponent uniqueness, and declaration truthfulness."""

    def __init__(self, prior_matches: list[PriorMatchRecord] | None = None) -> None:
        self.prior_matches: list[PriorMatchRecord] = list(prior_matches or [])

    def get_counted_matches(self) -> list[PriorMatchRecord]:
        return [m for m in self.prior_matches if m.mode.strip().lower() == "counted"]

    def get_distinct_opponents(self) -> set[str]:
        return {m.opponent_team for m in self.get_counted_matches()}

    def meets_submission_threshold(self) -> bool:
        """Check if at least 2 distinct counted opponents have been played (LEAGUE-002)."""
        return len(self.get_distinct_opponents()) >= MIN_COUNTED_MATCHES

    def validate_pairing(
        self,
        *,
        opponent_team: str,
        mode: str,
        declared_prior_count: int,
    ) -> bool:
        norm_mode = mode.strip().lower()
        if norm_mode not in ("counted", "warmup"):
            raise InvalidModeError(f"Invalid match mode '{mode}'; must be 'counted' or 'warmup'")

        if norm_mode == "warmup":
            # Warm-up matches do not count toward limits or opponent uniqueness
            return True

        counted_matches = self.get_counted_matches()
        if len(counted_matches) >= MAX_COUNTED_MATCHES:
            raise MaxMatchesExceededError(
                f"Cannot exceed maximum {MAX_COUNTED_MATCHES} counted matches (current: {len(counted_matches)})"
            )

        counted_opponents = self.get_distinct_opponents()
        if opponent_team in counted_opponents:
            raise DuplicateOpponentError(
                f"Already played counted match against opponent '{opponent_team}' (LEAGUE-003 limit: {MAX_MATCHES_PER_OPPONENT})"
            )

        if declared_prior_count != len(counted_matches):
            raise FalseDeclarationError(
                f"Declared prior matches ({declared_prior_count}) != recorded ({len(counted_matches)})"
            )

        return True

    def record_match(self, record: PriorMatchRecord) -> None:
        self.prior_matches.append(record)
