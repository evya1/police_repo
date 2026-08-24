"""Settling a played series: agree with the opponent, then publish (T058, CT-08).

Extracted from the runner so that module stays a process entrypoint rather than a place where
protocol decisions accumulate. The ordering here is the load-bearing part: the series engine
has already run the mutual log audit (App. E rule 36 makes it a precondition of agreeing), so
by the time anything below executes, the game is verified and only the settlement remains.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from common.transport.kit_agreement import AgreementOutcome, build_proposal
from common.transport.kit_identity import GroupIdentity, group_block
from common.transport.kit_names import result_name
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
    identity: GroupIdentity | None = None,
    opponent_identity: dict | None = None,
) -> Path | None:
    """Publish the kit projection beside the internal bundle.

    Deliberately non-fatal: the internal bundle is the evidence of record and is already on
    disk by the time we get here. A projection that cannot be written is a reporting problem
    to be seen and fixed, not a reason to lose a settled series.

    The kit projection carries only the kit's mandatory fields. Token usage is optional to
    the kit (its checker skips token gates when the keys are absent), so it is deliberately
    not projected here -- this also avoids fabricating a value for ``unknown`` usage.
    """
    try:
        counted = mode == "counted"
        groups = None
        games_played = None
        if identity is not None:
            theirs = opponent_identity or {"group_id": result.opponent_group_id}
            groups = sorted([group_block(identity), theirs], key=lambda item: item["group_id"])
            their_count = theirs.get("counted_games_played")
            games_played = {
                our_group: identity.counted_games_played + (1 if counted else 0),
                result.opponent_group_id: (
                    their_count + (1 if counted else 0)
                    if isinstance(their_count, int) else None
                ),
            }
        max_tokens = None
        if result.replay_evidence:
            terms = json.loads(result.replay_evidence[0].terms_bytes)
            max_tokens = terms.get("token_budget_per_series")
        # The kit projection carries only the kit's mandatory fields. Per-row `tokens` and
        # `final_result.tokens_total_series` are optional to the kit and would require
        # projecting a value for `unknown` usage, so they are omitted entirely.
        bundle = publish_kit_bundle(
            artifacts_dir, result, our_group=our_group, counted=counted,
            confirmed=confirmed, groups=groups, games_played=games_played,
            max_tokens_per_game=max_tokens,
            tokens_by_sub_game=None, include_tokens=False,
        )
        return bundle / result_name(result.game_id)
    except Exception as exc:  # noqa: BLE001 - never let a projection fault destroy evidence
        logger.error("Kit bundle projection failed (internal bundle is intact): %s", exc)
        return None
