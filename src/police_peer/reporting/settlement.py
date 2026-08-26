"""Settling a played series: agree with the opponent, then publish (T058, CT-08).

Extracted from the runner so that module stays a process entrypoint rather than a place where
protocol decisions accumulate. The ordering here is the load-bearing part: the series engine
has already run the mutual log audit (App. E rule 36 makes it a precondition of agreeing), so
by the time anything below executes, the game is verified and only the settlement remains.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from common.transport.kit_agreement import AgreementOutcome, build_proposal
from common.transport.kit_identity import GroupIdentity, group_block
from common.transport.kit_names import result_name
from common.transport.kit_settlement import result_row, series_final
from common.transport.series import SeriesResult
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.wire.result_agreement import exchange, exchange_token_evidence

logger = logging.getLogger(__name__)

NOT_SETTLED = "the series never settled, so there is nothing to agree"


def _time_bounds(evidence) -> tuple[str, str]:
    values = []
    for record in (*evidence.own_records, *evidence.opponent_records):
        value = json.loads(record.payload_bytes).get("timestamp")
        if isinstance(value, str):
            values.append(datetime.fromisoformat(value))
    if not values:
        raise ValueError("settlement evidence has no timestamp")
    israel = ZoneInfo("Asia/Jerusalem")
    return min(values).astimezone(israel).isoformat(), max(values).astimezone(israel).isoformat()


def settlement_rows(
    result: SeriesResult, *, our_group: str,
    tokens_by_sub_game: dict[int, dict[str, int]] | None = None,
    github_commit: dict[str, str] | None = None, counted: bool = False,
    games_played: dict[str, int | None] | None = None,
) -> tuple[list[dict], dict]:
    """The rows and derived aggregate both peers must produce identically."""
    theirs = result.opponent_group_id
    evidence = {item.sub_game_index: item for item in result.replay_evidence}
    rows = []
    for row in result.ledger:
        entry = result_row(
            row=row, our_group=our_group, opponent_group=theirs,
            tokens=(tokens_by_sub_game or {}).get(row.sub_game_number, {our_group: 0, theirs: 0}),
            log_file=f"log_{result.game_id}_g{row.sub_game_number:02d}.json",
            github_commit=github_commit,
        )
        entry["started_at"], entry["ended_at"] = _time_bounds(evidence[row.sub_game_number])
        rows.append(entry)
    return rows, series_final(
        rows, tuple(sorted([our_group, theirs])), counted=counted, games_played=games_played,
    )


def settle(
    channel, result: SeriesResult, *, our_group: str, budget: float,
    token_ledger=None, identity: GroupIdentity | None = None, mode: str = "warmup",
) -> AgreementOutcome:
    """Exchange settlement digests with the opponent and report what was agreed."""
    if not result.settled:
        return AgreementOutcome(False, NOT_SETTLED)
    if token_ledger is None or identity is None or not result.opponent_identity:
        return AgreementOutcome(False, "complete identity and token evidence are required")
    tokens = exchange_token_evidence(
        channel, token_ledger, game_id=result.game_id, game_uid=result.game_uid,
        our_group=our_group, opponent_group=result.opponent_group_id,
        counted=mode == "counted", budget=budget,
    )
    commits = {
        our_group: identity.github_commit,
        result.opponent_group_id: result.opponent_identity.get("github_commit"),
    }
    their_count = result.opponent_identity.get("counted_games_played")
    games_played = {
        our_group: identity.counted_games_played + (1 if mode == "counted" else 0),
        result.opponent_group_id: (
            their_count + (1 if mode == "counted" else 0)
            if isinstance(their_count, int) else None
        ),
    }
    rows, final = settlement_rows(
        result, our_group=our_group, tokens_by_sub_game=tokens,
        github_commit=commits, counted=mode == "counted", games_played=games_played,
    )
    proposal = build_proposal(result.game_id, result.game_uid, final, rows)
    outcome = exchange(channel, proposal, budget=budget)
    logger.info("Result agreement: agreed=%s (%s)", outcome.agreed, outcome.reason)
    return replace(outcome, rows=rows, final_result=final, tokens_by_sub_game=tokens)


def publish_kit(
    artifacts_dir: Path | str,
    result: SeriesResult,
    *,
    our_group: str,
    mode: str,
    confirmed: bool,
    identity: GroupIdentity | None = None,
    opponent_identity: dict | None = None,
    shared_config: dict | None = None,
    agreement: AgreementOutcome | None = None,
) -> Path | None:
    """Publish the official projection; incomplete mandatory evidence fails closed."""
    counted = mode == "counted"
    if identity is None or opponent_identity is None:
        raise ValueError("official publication requires both signed identities")
    groups = sorted(
        [group_block(identity), opponent_identity], key=lambda item: item["group_id"]
    )
    their_count = opponent_identity.get("counted_games_played")
    games_played = {
        our_group: identity.counted_games_played + (1 if counted else 0),
        result.opponent_group_id: (
            their_count + (1 if counted else 0) if isinstance(their_count, int) else None
        ),
    }
    max_tokens = (shared_config or {}).get("network_and_league", {}).get(
        "token_budget_per_series"
    )
    bundle = publish_kit_bundle(
        artifacts_dir, result, our_group=our_group, counted=counted,
        confirmed=confirmed, groups=groups, games_played=games_played,
        max_tokens_per_game=max_tokens,
        tokens_by_sub_game=(agreement.tokens_by_sub_game if agreement else None),
        agreed_config=shared_config,
        agreed_rows=(agreement.rows if agreement else None),
        agreed_final=(agreement.final_result if agreement else None), include_tokens=True,
    )
    return bundle / result_name(result.game_id)
