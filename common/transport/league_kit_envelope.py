"""Kit audit-envelope anti-corruption adapter (ADR-011, T052).

Converts between this project's flat sealed-record shape and the pinned
`copthief-league-protocol` kit's nested audit wire (`{"payload": <payload>,
"nonce": ..., "commit": ...}`) at the transport boundary only. Outbound wraps
the *exact* payload already committed -- it never re-hashes, so there is only
ever one commitment authority. Inbound normalizes a nested kit record back to
the flat shape T033's verifier (`common.transport.replay`) already decodes
strictly, without changing that verifier, its verdict taxonomy, or its
coverage discipline.

Also carries the SPEC 3.1 terminal-final and capture-corroboration
corrections as adapter-owned pure functions, layered onto the existing
`ReplayReport` taxonomy as an additional finding -- never a sixth verdict,
never a relabeling of a commitment/hash fault as anything but `TAMPERED`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from common.domain.board import Board
from common.transport.replay import verify_replay
from common.transport.replay_types import ReplayIssue, ReplayReport, ReplayVerdict

_ENVELOPE_KEYS = ("nonce", "commit")


def wrap_outbound(record: dict) -> dict:
    """Wrap one already-sealed flat record into the kit's nested envelope.

    `payload` is exactly the already-committed fields -- never reshaped, never re-hashed.
    """
    payload = {k: v for k, v in record.items() if k not in _ENVELOPE_KEYS}
    return {"payload": payload, "nonce": record["nonce"], "commit": record["commit"]}


def wrap_outbound_records(records: list[dict]) -> list[dict]:
    """Wrap a whole half's worth of sealed records."""
    return [wrap_outbound(r) for r in records]


def unwrap_inbound(record: dict) -> dict:
    """Normalize one nested kit record to this project's internal flat shape.

    A record with no `payload` key is left as-is (already flat, or malformed --
    that judgment belongs to `decode_record`, not this adapter).
    """
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return dict(record)
    flat = dict(payload)
    for key in _ENVELOPE_KEYS:
        if key in record:
            flat[key] = record[key]
    return flat


def unwrap_inbound_records(records: object) -> object:
    """Normalize a whole half's worth of records; non-list input passes through unchanged."""
    if not isinstance(records, list):
        return records
    return [unwrap_inbound(r) if isinstance(r, dict) else r for r in records]


def steps_agree(left_steps: int, right_steps: int) -> bool:
    """SPEC 3.1: peer step counts may differ by at most one (terminal-message perspective)."""
    return abs(int(left_steps) - int(right_steps)) <= 1


def terminal_step_delta_ok(prev: tuple[int, int] | None, curr: tuple[int, int] | None) -> bool:
    """A terminal `caught: true` final is exempt from the ordinary one-advance rule: a
    zero-step resend and a one-advance final are both legal, neither is required over the
    other. Unparseable input degrades to "ok" rather than accusing (nothing to compare)."""
    if prev is None or curr is None:
        return True
    return abs(curr[0] - prev[0]) + abs(curr[1] - prev[1]) <= 1


def parse_kit_position(payload: dict) -> tuple[int, int] | None:
    """Strictly parse a kit-style `position: [r, c]`. Anything else degrades to None --
    never a loose parse that could mis-read a malformed payload into the wrong cell."""
    pos = payload.get("position") if isinstance(payload, dict) else None
    if (
        isinstance(pos, (list, tuple))
        and len(pos) == 2
        and all(isinstance(v, int) and not isinstance(v, bool) for v in pos)
    ):
        return (int(pos[0]), int(pos[1]))
    return None


CaptureKind = Literal["answer", "concession"]


def classify_capture(
    cop_claim: tuple[int, int] | None, claim_response: dict | None
) -> CaptureKind | None:
    """SPEC 3.1: a `caught: true` echoing the cop's claim is an answer; naming any other
    cell is a concession. Not a `caught: true` final at all returns None."""
    if not isinstance(claim_response, dict) or claim_response.get("caught") is not True:
        return None
    claimed = claim_response.get("claim")
    if not isinstance(claimed, (list, tuple)) or len(claimed) != 2:
        return None
    claimed_cell = (claimed[0], claimed[1])
    if cop_claim is not None and tuple(cop_claim) == claimed_cell:
        return "answer"
    return "concession"


@dataclass(frozen=True, slots=True)
class KitCorroborationFinding:
    """One capture corroboration finding -- layered onto the existing verdict taxonomy,
    never a sixth verdict, never a relabeled commitment/hash (`TAMPERED`) fault."""

    kind: CaptureKind
    corroborated: bool
    reason: str


def corroborate_answer(claimed_cell, thief_trail_end) -> KitCorroborationFinding:
    """An answer's cell must be where the thief's own revealed trail ends."""
    ok = thief_trail_end is not None and tuple(thief_trail_end) == tuple(claimed_cell)
    reason = "" if ok else f"claimed {claimed_cell} but thief trail ends at {thief_trail_end}"
    return KitCorroborationFinding("answer", ok, reason)


def corroborate_concession(claimed_cell, cop_own_barriers, board_size: int) -> KitCorroborationFinding:
    """A concession's cell must be captured under the COP'S OWN barrier record (rule 46: a
    barrier on the cell; rule 47: boxed in) -- never the thief's reported barriers."""
    board = Board(size=board_size)
    barriers = set(cop_own_barriers or ())
    cell = tuple(claimed_cell)
    ok = cell in barriers or board.boxed_in(cell, barriers)
    reason = "" if ok else f"{cell} is neither a cop barrier nor boxed in by cop's own barriers"
    return KitCorroborationFinding("concession", ok, reason)


def evaluate_capture_corroboration(
    *,
    cop_claim: tuple[int, int] | None,
    claim_response: dict | None,
    thief_trail_end: tuple[int, int] | None,
    cop_own_barriers,
    board_size: int,
) -> KitCorroborationFinding | None:
    """Classify and corroborate one thief `caught: true` final, or None if it isn't one."""
    kind = classify_capture(cop_claim, claim_response)
    if kind is None:
        return None
    claimed = tuple(claim_response["claim"])  # type: ignore[index]
    if kind == "answer":
        return corroborate_answer(claimed, thief_trail_end)
    return corroborate_concession(claimed, cop_own_barriers, board_size)


def verify_kit_bundle(
    log_doc: dict, config_doc: dict, *, finding: KitCorroborationFinding | None = None
) -> ReplayReport:
    """Run the unmodified T033 verifier, then layer one corroboration finding on top.

    A failed corroboration is added as a distinct `ReplayIssue` and can only pull a clean
    `VERIFIED_OK` down to `ILLEGAL` -- an already `TAMPERED`/`INVALID`/`INCOMPLETE` report
    is returned untouched, so the existing verdict taxonomy is preserved exactly.
    """
    report = verify_replay(log_doc, config_doc)
    if finding is None or finding.corroborated:
        return report
    issues = (*report.issues, ReplayIssue("capture_corroboration_failed", finding.reason))
    verdict = ReplayVerdict.ILLEGAL if report.verdict == ReplayVerdict.VERIFIED_OK else report.verdict
    return ReplayReport(
        verdict=verdict, coverage=report.coverage, checked_records=report.checked_records, issues=issues
    )
