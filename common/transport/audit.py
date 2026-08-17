"""Mutual audit + TAMPERED sanction.

ST-09: three-layer audit — re-hash integrity, binding to the played map, and physics
armed from the 14 signed terms. One hash mismatch = total sanction, no repair path (FR-28/FR-29).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from common.transport.audit_physics import check_physics
from common.transport.canonical import canonical_bytes
from common.transport.canonical import commit as hash_commit


class AuditVerdict(StrEnum):
    PASSED = "passed"
    TAMPERED = "tampered"


@dataclass
class AuditResult:
    """Result of a mutual audit."""

    passed: bool = False
    verified_steps: int = 0
    failed_steps: list[int] = field(default_factory=list)
    tampered_steps: list[int] = field(default_factory=list)
    skipped: list[int] = field(default_factory=list)
    detail: str = ""

    @property
    def verdict(self) -> str:
        return AuditVerdict.TAMPERED if not self.passed else AuditVerdict.PASSED


def audit_records(
    records: list[dict],
    played: dict[int, str],
    terms: dict,
) -> AuditResult:
    """Three-layer audit: re-hash, binding, physics.

    Layer 1 (Integrity, always): every revealed record re-hashes to its own commit.
    Layer 2 (Binding, when played is given): revealed commits match what was received.
    Layer 3 (Physics, armed from terms): position trail, orthogonal step, barrier quota, step ceiling.
    """
    failed: list[int] = []
    tampered: list[int] = []
    skipped: list[int] = []
    notes: list[str] = []

    if not records:
        return AuditResult(passed=True, verified_steps=0)

    # --- Layer 1: Integrity — re-hash every record -------------------------------
    for record in records:
        step = int(record.get("step", -1))
        commit = record.get("commit")
        if commit is None:
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: missing commit")
            continue

        # The intent field must be declared (FR-42)
        intent = record.get("intent")
        if not intent or not isinstance(intent, str) or not intent.strip():
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: missing or empty intent field")
            continue

        # Re-hash: canonical(payload without commit+nonce) + nonce
        payload = {k: v for k, v in record.items() if k not in ("commit", "nonce")}
        nonce = record.get("nonce", "")
        computed = hash_commit(payload, nonce)
        if computed != commit:
            failed.append(step)
            tampered.append(step)
            if len(notes) < 3:
                notes.append(
                    f"step {step}: committed {commit}, rehash {computed}\n"
                    f"      canonical form: {canonical_bytes(payload).decode('utf-8')}"
                )
            continue

        # Layer 2: Binding against the played map
        if step >= 1 and step in played and played[step] != commit:
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: binding mismatch — played {played[step]}, revealed {commit}")
            continue

    # --- Layer 3: Physics -------------------------------------------------------
    physics_problems = check_physics(records, terms)
    for step, problem in physics_problems:
        if step not in failed:
            failed.append(step)
            notes.append(f"step {step}: {problem}")

    passed = len(failed) == 0
    verified = len([r for r in records if int(r.get("step", 0)) >= 1])
    detail = "; ".join(notes[:3]) if notes else ""

    return AuditResult(
        passed=passed,
        verified_steps=verified,
        failed_steps=failed,
        tampered_steps=tampered,
        skipped=skipped,
        detail=detail,
    )


def audit_verdict(result: AuditResult) -> str:
    """Return TAMPERED or PASSED string."""
    return result.verdict


def tampered_sanction() -> tuple[int, int]:
    """Return the (police, thief) score for a TAMPERED sub-game.

    FR-29: both zeroed, no repair path.
    """
    return (0, 0)
