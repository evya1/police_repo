"""Mutual audit + TAMPERED sanction.

STUB — to be replaced by the real implementation in ST-09 (T008).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AuditVerdict(StrEnum):
    PASSED = "passed"
    TAMPERED = "tampered"


@dataclass
class AuditResult:
    """Result of a mutual audit."""

    passed: bool = False
    verified_steps: int = 0
    failed_steps: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)


def audit_records(
    records: list[dict],
    played: dict[int, str],
    terms: dict,
) -> AuditResult:
    """Three-layer audit: re-hash, binding, physics.

    STUB: always-pass placeholder.
    Layer 1: re-hash every revealed record with our own serializer.
    Layer 2: binding against the inbox `played` map.
    Layer 3: physics armed from the 14 terms.
    """
    # STUB: always pass
    return AuditResult(passed=True, verified_steps=len(records))


def audit_verdict(result: AuditResult) -> str:
    """Return TAMPERED or PASSED string."""
    return result.verdict


def tampered_sanction() -> tuple[int, int]:
    """Return the (police, thief) score for a TAMPERED sub-game.

    FR-29: both zeroed, no repair path.
    """
    return (0, 0)
