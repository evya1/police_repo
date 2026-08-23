"""Layer-4 outcome checks and supporting pure helpers for replay verification.

Split out of ``replay.py`` to keep the 150-logical-line cap (AGENTS.md): these are
pure functions with no dependency on ``verify_replay``'s control flow — parsing board
state out of a logged position string, answering a capture claim against the thief's
pre-move snapshot, validating ``win_claim`` (Layer 4) semantics, and detecting
withheld reveals against a committed-steps ledger.
"""

from __future__ import annotations

import re

from common.domain.board import Board
from common.domain.scoring import Role
from common.transport.audit_physics import _parse_position
from common.transport.replay_records import missing_steps
from common.transport.replay_types import ReplayIssue, SealedRecord

_BARRIERS_RE = re.compile(r"barriers=\[(.*)\]")
_CELL_RE = re.compile(r"\[(\d+),\s*(\d+)\]")


def _parse_barriers(state: str) -> set[tuple[int, int]]:
    match = _BARRIERS_RE.search(state)
    if not match:
        return set()
    return {(int(r), int(c)) for r, c in _CELL_RE.findall(match.group(1))}


def _claim_answered(record: dict, by_step: dict[int, dict], step: int) -> bool:
    """A capture claim is answered against the thief's *pre-move* snapshot (GAME-009/SEC-007)."""
    resp = record.get("claim_response")
    if not resp or resp.get("caught") is not True:
        return False
    prev = by_step.get(step - 1)
    pre_pos = _parse_position(prev.get("state", "")) if prev else None
    claimed = resp.get("claim")
    return pre_pos is not None and claimed is not None and tuple(pre_pos) == tuple(claimed)


def _outcome_issues(flat: list[dict], terms: dict, half: str) -> list[ReplayIssue]:
    """Layer 4: capture/survival ``win_claim`` semantics — thief-only, role- and board-checked."""
    board = Board(size=int(terms.get("board_size", 7)))
    threshold = int(terms.get("survival_threshold", terms.get("max_steps", 35)))
    by_step = {r["step"]: r for r in flat}
    issues: list[ReplayIssue] = []
    for r in flat:
        step, claim = r["step"], r.get("win_claim")
        if step < 1 or not claim:
            continue
        role, ctype = r.get("sender"), claim.get("type")
        if ctype == "survival":
            if role != Role.THIEF.value or step < threshold:
                msg = f"survival claim invalid for role={role} at step {step}"
                issues.append(ReplayIssue("invalid_survival_claim", msg, step, half))
        elif ctype == "capture":
            pos = _parse_position(r.get("state", ""))
            barriers = _parse_barriers(r.get("state", ""))
            caught = _claim_answered(r, by_step, step)
            valid = (
                role == Role.THIEF.value
                and pos is not None
                and (caught or pos in barriers or board.boxed_in(pos, barriers))
            )
            if not valid:
                msg = f"capture claim invalid for role={role} at step {step}"
                issues.append(ReplayIssue("invalid_capture_claim", msg, step, half))
    return issues


def _gap_is_withheld(
    decode_issues: list[ReplayIssue], sealed: list[SealedRecord], committed: list[int] | None
) -> bool:
    """True when a decode-time sequence gap is fully explained by the committed-steps ledger.

    A missing record is malformed evidence (INVALID) only when nothing proves it was ever
    committed. When the ledger lists a step absent from the half's records, the gap is a
    withheld reveal instead — TAMPERED, not INVALID (ADR-008; mirrors audit.py's
    ``tampered_steps``). Any other decode issue (bad type, duplicate/out-of-order step, mixed
    shape, …) still forces INVALID unconditionally: only a clean contiguity gap is reinterpreted,
    and only when a ledger is actually supplied to prove it against.
    """
    if committed is None or any(i.code != "skipped_step" for i in decode_issues):
        return False
    gap = missing_steps(sealed)
    return bool(gap) and set(gap) <= set(committed)


def _withheld_issues(committed: list[int] | None, revealed: set[int], half: str) -> list[ReplayIssue]:
    """Mirrors audit.py's withheld-reveal logic — only when the doc supplies committed steps."""
    if committed is None:
        return []
    withheld = sorted(set(committed) - revealed)
    return [
        ReplayIssue("withheld_reveal", f"step {s} committed but never revealed", s, half)
        for s in withheld
    ]
