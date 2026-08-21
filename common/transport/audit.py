"""Mutual audit + TAMPERED sanction.

ST-09: three-layer audit — re-hash integrity, binding to the played map, and physics
armed from the 14 signed terms. One hash mismatch = total sanction, no repair path (FR-28/FR-29).
Layer 4 outcome semantics checks result claims, capture verification, and survival boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from common.domain.board import Board
from common.domain.scoring import Role
from common.transport.audit_physics import _parse_position, check_physics
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
    our_records: list[dict] | None = None,
    our_result_claim: str | None = None,
    opponent_result_claim: str | None = None,
) -> AuditResult:
    """Four-layer audit: re-hash, binding, physics, outcome semantics."""
    failed: list[int] = []
    tampered: list[int] = []
    skipped: list[int] = []
    notes: list[str] = []

    # A reveal must account for every step that was actually committed on the wire.
    # Verifying only the records we are handed lets a peer drop the step it tampered
    # with -- or reveal nothing at all -- and still settle clean.
    revealed = {int(r.get("step", -1)) for r in records}
    withheld = sorted(step for step in played if step not in revealed)
    if withheld:
        failed.extend(withheld)
        tampered.extend(withheld)
        notes.append(f"withheld reveal for committed step(s) {withheld}")

    # --- Layer 1: Integrity — re-hash every record -------------------------------
    for record in records:
        step = int(record.get("step", -1))
        commit = record.get("commit")
        if commit is None:
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: missing commit")
            continue

        intent = record.get("intent")
        if not intent or not isinstance(intent, str) or not intent.strip():
            failed.append(step)
            tampered.append(step)
            notes.append(f"step {step}: missing or empty intent field")
            continue

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

    # --- Layer 4: Outcome Semantics & Result Claim -----------------------------
    if (
        our_result_claim is not None
        and opponent_result_claim is not None
        and our_result_claim != opponent_result_claim
    ):
        failed.append(0)
        tampered.append(0)
        notes.append(
            f"result_claim mismatch: our {our_result_claim} vs opponent {opponent_result_claim}"
        )

    if our_records is not None:
        audited_role = None
        for r in records:
            if "sender" in r:
                audited_role = r["sender"]
                break

        survival_threshold = int(terms.get("survival_threshold", terms.get("max_steps", 35)))

        for r in records:
            step = int(r.get("step", -1))
            if step < 1:
                continue

            if audited_role == Role.THIEF.value:
                win_claim = r.get("win_claim")
                if win_claim:
                    claim_type = win_claim.get("type")
                    if claim_type == "survival":
                        if step < survival_threshold and step not in failed:
                            failed.append(step)
                            notes.append(
                                f"step {step}: invalid survival claim before survival_threshold ({survival_threshold})"
                            )
                    elif claim_type == "capture":
                        state_str = r.get("state", "")
                        thief_pos = _parse_position(state_str)
                        barriers = set()
                        b_part = state_str[state_str.find("barriers="):] if "barriers=" in state_str else ""
                        b_strs = re.findall(r"\[(\d+),\s*(\d+)\]", b_part)
                        if b_strs:
                            barriers = {(int(rr), int(cc)) for rr, cc in b_strs}

                        board = Board(size=terms.get("board_size", 7))
                        claim_resp = r.get("claim_response")
                        is_claim_caught = False
                        if claim_resp and claim_resp.get("caught") is True:
                            cpos = claim_resp.get("claim")
                            if cpos and thief_pos and tuple(thief_pos) == tuple(cpos):
                                is_claim_caught = True

                        if thief_pos:
                            r46 = thief_pos in barriers
                            r47 = board.boxed_in(thief_pos, barriers)
                            if not (is_claim_caught or r46 or r47) and step not in failed:
                                failed.append(step)
                                notes.append(f"step {step}: invalid capture claim")

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
    """Return the (police, thief) score for a TAMPERED sub-game."""
    return (0, 0)
