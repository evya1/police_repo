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

from common.transport.audit_physics import check_physics
from common.transport.canonical import verify_commit
from common.transport.replay_layers import _gap_is_withheld, _outcome_issues, _withheld_issues
from common.transport.replay_records import decode_half, is_foreign_record
from common.transport.replay_types import (
    ReplayIssue,
    ReplayReport,
    ReplayVerdict,
    VerificationCoverage,
)

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
    for half, raw, committed in halves:
        sealed, decode_issues = decode_half(raw, half)
        checked += len(sealed)
        if decode_issues and not _gap_is_withheld(decode_issues, sealed, committed):
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
