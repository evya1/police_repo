"""Pure replay verification — reproduces the four-layer live audit offline from parsed
documents only. No filesystem, clock, or network: the caller supplies ``log_doc``/``config_doc``
already parsed; file discovery and bundle membership are a later task (T047), not this one.

Trust statement (ARCHITECTURE_AUDIT): a matching commit proves only that the revealed payload
matches that commit. A party able to rewrite payload, nonce, commit, and manifest together can
make an unanchored local bundle internally consistent, so ``VERIFIED_OK`` here means "every
locally available check passed" — never "historically authentic" (see ``external_authenticity``).
"""

from __future__ import annotations

import json
import re

from common.domain.board import Board
from common.domain.scoring import Role
from common.transport.audit_physics import _parse_position, check_physics
from common.transport.canonical import verify_commit
from common.transport.replay_records import decode_half, is_foreign_record
from common.transport.replay_types import (
    ReplayIssue,
    ReplayReport,
    ReplayVerdict,
    VerificationCoverage,
)

_BARRIERS_RE = re.compile(r"barriers=\[(.*)\]")
_CELL_RE = re.compile(r"\[(\d+),\s*(\d+)\]")
_TAMPER_CODES = ("commitment_mismatch", "withheld_reveal")
_NO_COVERAGE = VerificationCoverage(False, False, False, False, False, False)
_IDENTITY_KEYS = ("game_uid", "game_id", "sub_game_index")


def _report(
    verdict: ReplayVerdict, coverage: VerificationCoverage, checked: int, issues: list[ReplayIssue]
) -> ReplayReport:
    return ReplayReport(verdict=verdict, coverage=coverage, checked_records=checked, issues=tuple(issues))


def _check_identity(log_doc: object, config_doc: object) -> list[ReplayIssue]:
    """Exact pairing: same game_uid, game_id, and sub_game_index — never "the first config"."""
    if not isinstance(log_doc, dict) or not isinstance(config_doc, dict):
        return [ReplayIssue("bad_document", "log_doc and config_doc must both be objects")]
    issues: list[ReplayIssue] = []
    for key in _IDENTITY_KEYS:
        if key not in log_doc or key not in config_doc:
            issues.append(ReplayIssue("missing_identity", f"'{key}' missing from log or config"))
        elif log_doc[key] != config_doc[key]:
            msg = f"{key} mismatch: log={log_doc.get(key)!r} config={config_doc.get(key)!r}"
            issues.append(ReplayIssue("identity_mismatch", msg))
    return issues


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


def _withheld_issues(committed: list[int] | None, revealed: set[int], half: str) -> list[ReplayIssue]:
    """Mirrors audit.py's withheld-reveal logic — only when the doc supplies committed steps."""
    if committed is None:
        return []
    withheld = sorted(set(committed) - revealed)
    return [
        ReplayIssue("withheld_reveal", f"step {s} committed but never revealed", s, half)
        for s in withheld
    ]


def verify_replay(log_doc: dict, config_doc: dict) -> ReplayReport:
    """Verify one log against its exact config. Pure: no I/O, no clock, no guessed shape."""
    id_issues = _check_identity(log_doc, config_doc)
    if id_issues:
        return _report(ReplayVerdict.INVALID, _NO_COVERAGE, 0, id_issues)

    terms = config_doc.get("terms")
    if not isinstance(terms, dict):
        return _report(
            ReplayVerdict.INCOMPLETE, _NO_COVERAGE, 0,
            [ReplayIssue("missing_terms", "config_doc has no 'terms' object")],
        )

    own_raw = log_doc.get("records")
    if not isinstance(own_raw, list) or not own_raw:
        return _report(
            ReplayVerdict.INCOMPLETE, _NO_COVERAGE, 0,
            [ReplayIssue("no_records", "log_doc has no own records")],
        )

    halves = [("own", own_raw, log_doc.get("own_committed_steps"))]
    opp_raw = log_doc.get("opponent_records")
    if opp_raw is not None:
        if not isinstance(opp_raw, list) or not opp_raw:
            return _report(
                ReplayVerdict.INCOMPLETE, _NO_COVERAGE, 0,
                [ReplayIssue("empty_opponent_half", "opponent_records is present but empty")],
            )
        halves.append(("opponent", opp_raw, log_doc.get("opponent_committed_steps")))

    sealed_by_half = {}
    checked = 0
    for half, raw, _committed in halves:
        sealed, decode_issues = decode_half(raw, half)
        checked += len(sealed)
        if decode_issues:
            return _report(ReplayVerdict.INVALID, _NO_COVERAGE, checked, decode_issues)
        sealed_by_half[half] = sealed

    issues: list[ReplayIssue] = []
    binding_supplied = True
    all_native = True
    for half, _raw, committed in halves:
        sealed = sealed_by_half[half]
        flat = [json.loads(r.payload_bytes) for r in sealed]
        for rec, payload in zip(sealed, flat, strict=True):
            if not verify_commit(payload, rec.nonce, rec.commitment):
                msg = f"step {rec.step}: revealed payload does not reproduce its commitment"
                issues.append(ReplayIssue("commitment_mismatch", msg, rec.step, half))

        binding_supplied = binding_supplied and committed is not None
        issues.extend(_withheld_issues(committed, {r.step for r in sealed}, half))

        if any(r["step"] >= 1 and is_foreign_record(r) for r in flat):
            all_native = False
            continue
        issues.extend(
            ReplayIssue("physics_violation", problem, step, half)
            for step, problem in check_physics(flat, terms)
        )
        issues.extend(_outcome_issues(flat, terms, half))

    coverage = VerificationCoverage(
        integrity=True,
        live_binding=binding_supplied,
        physics=all_native,
        outcome=all_native,
        bundle_digests=False,
        external_authenticity=False,
    )

    if any(i.code in _TAMPER_CODES for i in issues):
        return _report(ReplayVerdict.TAMPERED, coverage, checked, issues)
    if issues:
        return _report(ReplayVerdict.ILLEGAL, coverage, checked, issues)
    return _report(ReplayVerdict.VERIFIED_OK, coverage, checked, issues)
