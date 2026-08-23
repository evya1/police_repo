"""Strict record decoding: kit-nested and repo-flat record shapes into frozen SealedRecords.

A record is either nested (``{"payload": {...}, "nonce": ..., "commit": ...}``) or flat
(``{...payload fields..., "nonce": ..., "commit": ...}``) — both encode the same payload. This
module normalizes either into one immutable ``SealedRecord`` and validates the whole sequence.
No hash is computed here — that is ``verify_replay``'s job, using the frozen canonical bytes.
"""

from __future__ import annotations

import re

from common.transport.canonical import canonical_bytes
from common.transport.replay_types import ReplayIssue, SealedRecord

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_STATE_RE = re.compile(r"self=\[(-?\d+),\s*(-?\d+)\]")


class RecordDecodeError(Exception):
    """Raised by ``decode_record`` for any structural, type, or shape violation."""

    def __init__(self, code: str, message: str, step: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.step = step


def _shape_of(raw: object) -> str:
    """'nested' (has payload), 'flat' (has step at top level), or 'unknown'."""
    if not isinstance(raw, dict):
        return "unknown"
    if "payload" in raw:
        return "nested"
    if "step" in raw:
        return "flat"
    return "unknown"


def decode_record(raw: dict) -> SealedRecord:
    """Strictly decode one nested-or-flat record. Raises RecordDecodeError on any violation.

    Booleans are rejected where an int is required (``isinstance(True, int)`` is True in
    Python, so ``step`` is checked with an explicit ``type(...) is bool`` guard).
    """
    shape = _shape_of(raw)
    if shape == "unknown":
        raise RecordDecodeError("unknown_shape", "record has neither 'payload' nor 'step'")

    if shape == "nested":
        payload = raw.get("payload")
        if not isinstance(payload, dict):
            raise RecordDecodeError("bad_payload", "nested record payload is not an object")
    else:
        payload = {k: v for k, v in raw.items() if k not in ("nonce", "commit")}

    step = payload.get("step")
    if type(step) is bool or not isinstance(step, int) or step < 0:
        raise RecordDecodeError("bad_step", f"step must be a non-negative int, got {step!r}")

    nonce = raw.get("nonce")
    if not isinstance(nonce, str) or not nonce:
        raise RecordDecodeError("bad_nonce", "nonce must be a non-empty string", step)

    commitment = raw.get("commit")
    if not isinstance(commitment, str) or not _HEX64.match(commitment):
        raise RecordDecodeError(
            "bad_commitment", "commitment must be 64 lowercase hex chars", step
        )

    return SealedRecord(
        step=step, payload_bytes=canonical_bytes(payload), nonce=nonce, commitment=commitment
    )


def decode_half(raw_records: object, half: str) -> tuple[list[SealedRecord], list[ReplayIssue]]:
    """Decode one half's record list: homogeneous shape, per-record strictness, step sequence.

    A mix of nested and flat records inside one half is rejected outright (INVALID territory)
    rather than guessed at — the deleted first-record heuristic inferred shape from one record
    and misclassified the whole half; this checks every record's shape instead.
    """
    if not isinstance(raw_records, list):
        return [], [ReplayIssue("bad_half_shape", "records must be a list", half=half)]

    shapes = {_shape_of(r) for r in raw_records}
    if len(shapes) > 1:
        msg = f"half mixes record shapes {sorted(shapes)}"
        return [], [ReplayIssue("mixed_shape", msg, half=half)]

    records: list[SealedRecord] = []
    issues: list[ReplayIssue] = []
    for raw in raw_records:
        try:
            records.append(decode_record(raw))
        except RecordDecodeError as exc:
            issues.append(ReplayIssue(exc.code, exc.message, exc.step, half))

    if issues:
        return records, issues
    return records, _check_sequence(records, half)


def missing_steps(records: list[SealedRecord]) -> list[int]:
    """Steps absent from a contiguous 0..len(unique steps)-1 run, sorted ascending.

    Exposed separately from ``_check_sequence`` so a caller (``verify_replay``) can test a
    contiguity gap against a committed-steps ledger without parsing an issue message.
    """
    seen = {r.step for r in records}
    return sorted(set(range(len(seen))) - seen)


def _check_sequence(records: list[SealedRecord], half: str) -> list[ReplayIssue]:
    """Steps must be unique, strictly increasing in list order, and contiguous from 0."""
    issues: list[ReplayIssue] = []
    seen: set[int] = set()
    prev: int | None = None
    for rec in records:
        if rec.step in seen:
            issues.append(ReplayIssue("duplicate_step", f"step {rec.step} repeats", rec.step, half))
        elif prev is not None and rec.step <= prev:
            msg = f"step {rec.step} does not follow step {prev}"
            issues.append(ReplayIssue("out_of_order_step", msg, rec.step, half))
        seen.add(rec.step)
        prev = rec.step
    missing = missing_steps(records)
    if missing:
        issues.append(ReplayIssue("skipped_step", f"missing step(s) {missing}", half=half))
    return issues


def is_foreign_record(payload: dict) -> bool:
    """True when the payload carries no parseable repo-state string (kit/foreign shape, D-03).

    Foreign kit shape uses position lists instead of the repo's
    ``grid=…;self=[r, c];barriers=…`` string. A record whose payload lacks a parseable
    ``state`` is foreign — the verifier reports it integrity-only, with degraded coverage.
    """
    state = payload.get("state", "")
    if not state or not isinstance(state, str):
        return True
    return _STATE_RE.search(state) is None
