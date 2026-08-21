from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from common.transport.canonical import canonical_bytes

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


class SignatureVerificationError(LeagueEligibilityError):
    """Raised when a prior match record signature fails verification."""


class MissingCredentialError(LeagueEligibilityError):
    """Raised when required credential/metadata is absent for counted mode."""


class PairingHistoryStore(Protocol):
    """Durable store for pairing history records."""

    def load(self) -> list[PriorMatchRecord]: ...
    def save(self, records: list[PriorMatchRecord]) -> None: ...


class FilePairingHistoryStore:
    """File-based pairing history persisted to JSON."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path(".pairing_history.json")

    def load(self) -> list[PriorMatchRecord]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return [PriorMatchRecord(**r) for r in data]
        except (json.JSONDecodeError, TypeError):
            return []

    def save(self, records: list[PriorMatchRecord]) -> None:
        serializable = []
        for r in records:
            serializable.append({
                "game_uid": r.game_uid,
                "opponent_team": r.opponent_team,
                "mode": r.mode,
                "timestamp": r.timestamp,
                "signature": r.signature,
                "extra_evidence": r.extra_evidence,
            })
        self._path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


class CredentialMetadataProvider(Protocol):
    """Injected credential/metadata seam with NO invented defaults.

    If provided, validate_pairing checks that required fields are present
    (fail closed if absent for counted mode). If not provided, skips
    credential checks (backward compat). Never fabricates metadata.
    """

    def team(self) -> str | None: ...
    def opponent(self) -> str | None: ...
    def endpoint(self) -> str | None: ...
    def hardware(self) -> str | None: ...
    def model(self) -> str | None: ...
    def token_budget(self) -> int | None: ...


def verify_prior_match_signature(
    record: PriorMatchRecord, verifier: Callable[[bytes, str], bool]
) -> bool:
    """Verify a PriorMatchRecord signature using the injected verifier."""
    if not record.signature:
        return True  # no signature to verify — backward compat
    payload = {
        "game_uid": record.game_uid,
        "opponent_team": record.opponent_team,
        "mode": record.mode,
        "timestamp": record.timestamp,
    }
    data = canonical_bytes(payload)
    return verifier(data, record.signature)


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

    def __init__(
        self,
        prior_matches: list[PriorMatchRecord] | None = None,
        *,
        verifier: Callable[[bytes, str], bool] | None = None,
        history_store: PairingHistoryStore | None = None,
        credential_provider: CredentialMetadataProvider | None = None,
    ) -> None:
        self.verifier = verifier
        self.credential_provider = credential_provider
        if history_store is not None:
            self._history_store = history_store
            self.prior_matches = history_store.load()
        else:
            self._history_store = None
            self.prior_matches = list(prior_matches or [])

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

        # Verify signatures on prior matches if verifier is provided (T020)
        if self.verifier is not None:
            for m in counted_matches:
                if not verify_prior_match_signature(m, self.verifier):
                    raise SignatureVerificationError(
                        f"Prior match {m.game_uid} has invalid signature"
                    )

        # Credential/metadata check for counted mode (fail closed if provider is set)
        if self.credential_provider is not None:
            for field_name, value in [
                ("team", self.credential_provider.team()),
                ("opponent", self.credential_provider.opponent()),
                ("endpoint", self.credential_provider.endpoint()),
                ("hardware", self.credential_provider.hardware()),
                ("model", self.credential_provider.model()),
            ]:
                if value is None:
                    raise MissingCredentialError(
                        f"Required credential/metadata '{field_name}' is absent for counted mode"
                    )

        return True

    def record_match(self, record: PriorMatchRecord) -> None:
        if self.verifier is not None and not verify_prior_match_signature(record, self.verifier):
            raise SignatureVerificationError(
                f"Cannot record match with invalid signature: {record.game_uid}"
            )
        self.prior_matches.append(record)
        if self._history_store is not None:
            self._history_store.save(self.prior_matches)
