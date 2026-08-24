"""Settling a played series: agree with the opponent, then publish (T058, CT-08).

Extracted from the runner so that module stays a process entrypoint rather than a place where
protocol decisions accumulate. The ordering here is the load-bearing part: the series engine
has already run the mutual log audit (App. E rule 36 makes it a precondition of agreeing), so
by the time anything below executes, the game is verified and only the settlement remains.
"""

from __future__ import annotations

import logging
from pathlib import Path

from common.transport.kit_agreement import AgreementOutcome, build_proposal
from common.transport.kit_settlement import result_row, series_final
from common.transport.series import SeriesResult
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.wire.result_agreement import exchange

logger = logging.getLogger(__name__)

NOT_SETTLED = "the series never settled, so there is nothing to agree"


def settlement_rows(result: SeriesResult, *, our_group: str) -> tuple[list[dict], dict]:
    """The rows and derived aggregate both peers must produce identically."""
    theirs = result.opponent_group_id
    rows = [
        result_row(
            row=row, our_group=our_group, opponent_group=theirs,
            tokens={our_group: 0, theirs: 0},
            log_file=f"log_{result.game_id}_g{row.sub_game_number:02d}.json",
        )
        for row in result.ledger
    ]
    return rows, series_final(rows, tuple(sorted([our_group, theirs])), counted=False)


def settle(channel, result: SeriesResult, *, our_group: str, budget: float) -> AgreementOutcome:
    """Exchange settlement digests with the opponent and report what was agreed."""
    if not result.settled:
        return AgreementOutcome(False, NOT_SETTLED)
    rows, final = settlement_rows(result, our_group=our_group)
    proposal = build_proposal(result.game_id, result.game_uid, final, rows)
    outcome = exchange(channel, proposal, budget=budget)
    logger.info("Result agreement: agreed=%s (%s)", outcome.agreed, outcome.reason)
    return outcome


def publish_kit(
    artifacts_dir: Path | str,
    result: SeriesResult,
    *,
    our_group: str,
    mode: str,
    confirmed: bool,
) -> None:
    """Publish the kit projection beside the internal bundle.

    Deliberately non-fatal: the internal bundle is the evidence of record and is already on
    disk by the time we get here. A projection that cannot be written is a reporting problem
    to be seen and fixed, not a reason to lose a settled series.
    """
    try:
        publish_kit_bundle(
            artifacts_dir, result, our_group=our_group, counted=(mode == "counted"),
            confirmed=confirmed,
        )
    except Exception as exc:  # noqa: BLE001 - never let a projection fault destroy evidence
        logger.error("Kit bundle projection failed (internal bundle is intact): %s", exc)
