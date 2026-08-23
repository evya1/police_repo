"""Frozen replay verification types — the shared vocabulary of ``verify_replay``.

No behavior lives here: only immutable data. Every type is deliberately explicit so a caller
can never coerce partial evidence into a stronger verdict or a broader coverage claim than what
was actually checked (ARCHITECTURE_AUDIT trust statement).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReplayVerdict(StrEnum):
    """Final replay outcome. Distinct causes never collapse into one bucket."""

    VERIFIED_OK = "verified_ok"
    TAMPERED = "tampered"
    ILLEGAL = "illegal"
    INVALID = "invalid"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class SealedRecord:
    """One strictly decoded record, holding the exact bytes that were hashed.

    ``payload_bytes`` is the canonical UTF-8 form of the decoded payload
    (``canonical_bytes``), captured once at decode time so a caller cannot mutate a nested
    dict after validation and drift from what was actually verified.
    """

    step: int
    payload_bytes: bytes
    nonce: str
    commitment: str


@dataclass(frozen=True, slots=True)
class ReplayIssue:
    """One concrete problem found during verification, tied to a step/half where known."""

    code: str
    message: str
    step: int | None = None
    half: str | None = None


@dataclass(frozen=True, slots=True)
class VerificationCoverage:
    """Which layers were actually evaluated. Each boolean is independent of the others and of
    whether that layer passed — a layer can be checked (True) and still fail."""

    integrity: bool
    live_binding: bool
    physics: bool
    outcome: bool
    bundle_digests: bool
    external_authenticity: bool


@dataclass(frozen=True, slots=True)
class ReplayReport:
    """The full outcome of verifying one log against its config: verdict, coverage, evidence."""

    verdict: ReplayVerdict
    coverage: VerificationCoverage
    checked_records: int
    issues: tuple[ReplayIssue, ...]
