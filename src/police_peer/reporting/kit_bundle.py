"""Project one settled series into the league kit's 14-artifact bundle (ADR-012, CT-07, T056).

Everything here reads evidence that is already sealed and writes it in a different shape. The
records go through ``league_kit_envelope.wrap_outbound_records``, which wraps the exact bytes
that were committed; the terms come from ``evidence.terms_bytes``, the sealed bytes the uid was
derived from, never a fresh projection. Nothing on this path hashes a game payload.

The self-verification below is the one place that re-hashes, and it does so AFTER writing, on
what was actually written: reload every log and reproduce every commit. It is a check on our
own serialization, not a second commitment authority -- if it ever disagrees with the seal, the
bundle is not published and the seal is right.
"""

from __future__ import annotations

import json
from pathlib import Path

from common.transport.atomic_publish import Checkpoint, SelfVerifyError
from common.transport.kit_consensus import mutual_agreement
from common.transport.kit_documents import (
    build_config,
    build_declaration,
    build_log,
    build_result,
)
from common.transport.kit_names import config_name, declaration_name, log_name, result_name
from common.transport.kit_settlement import result_row, series_final
from common.transport.series import SeriesResult
from police_peer.reporting.kit_bundle_documents import document_bytes, records, summary

#: Official Appendix-F files are isolated from the richer internal replay bundle.
KIT_SUBDIR = "official"


def build_kit_bundle(
    result: SeriesResult,
    *,
    our_group: str,
    counted: bool,
    groups: list[dict] | None = None,
    agreed_config: dict | None = None,
    step_zero: dict | None = None,
    github: dict | None = None,
    league: dict | None = None,
    max_tokens_per_game: int | None = None,
    tokens_by_sub_game: dict[int, dict[str, int]] | None = None,
    games_played: dict[str, int | None] | None = None,
    agreed_rows: list[dict] | None = None,
    agreed_final: dict | None = None,
    first_meeting: bool = True,
    confirmed: bool = False,
    include_tokens: bool = True,
) -> dict[str, bytes]:
    """Build 14 files from complete identity, config, Git, token and sealed game evidence."""
    ours, theirs = our_group, result.opponent_group_id
    if not ours or not theirs:
        raise SelfVerifyError(
            "no opponent group id on the series result, so no per-group projection is possible "
            "-- the greeting must have resolved before a bundle is built"
        )
    pair = tuple(sorted([ours, theirs]))
    if not groups or len(groups) != 2:
        raise SelfVerifyError("official declaration requires two complete signed group blocks")
    if agreed_config is None:
        raise SelfVerifyError("official config requires the complete agreed shared configuration")
    if not include_tokens or tokens_by_sub_game is None:
        raise SelfVerifyError("official result requires truthful per-sub-game token evidence")
    group_by_id = {group.get("group_id"): group for group in groups}
    if set(group_by_id) != set(pair):
        raise SelfVerifyError("official group identities do not match the settled pair")
    commits = {group: group_by_id[group].get("github_commit") for group in pair}
    if any(not isinstance(value, str) or len(value) != 40 for value in commits.values()):
        raise SelfVerifyError("official result requires both 40-character Git commits")
    game_id, uid = result.game_id, result.game_uid
    ids = {"game_id": game_id, "game_uid": uid}
    github_links = github or {group: group_by_id[group].get("repos") for group in pair}
    common = {"league": league, "github": github_links}

    files: dict[str, bytes] = {}
    rows: list[dict] = []
    by_number = {row.sub_game_number: row for row in result.ledger}

    for evidence in sorted(result.replay_evidence, key=lambda e: e.sub_game_index):
        number = evidence.sub_game_index
        row = by_number[number]
        files[config_name(game_id, number)] = document_bytes(
            build_config(**ids, sub_game_number=number, terms=agreed_config, **common)
        )
        token_row = tokens_by_sub_game.get(number)
        if not isinstance(token_row, dict) or set(token_row) != set(pair):
            raise SelfVerifyError(f"sub-game {number} lacks complete per-group token evidence")
        entry = result_row(
            row=row, our_group=ours, opponent_group=theirs,
            tokens=token_row,
            log_file=log_name(game_id, number),
            github_commit=commits,
        )
        rows.append(entry)
        log_summary = summary(
            evidence, row, number=number, ours=ours, theirs=theirs,
            winner=entry["winner_group"],
        )
        log_summary["tokens_total"] = token_row[ours]
        entry["started_at"] = log_summary["started_at"]
        entry["ended_at"] = log_summary["ended_at"]
        files[log_name(game_id, number)] = document_bytes(
            build_log(
                **ids, sub_game_number=number, summary=log_summary,
                records=records(evidence.own_records),
                opponent_records=(
                    records(evidence.opponent_records) if evidence.opponent_records else None
                ),
                opponent_committed_steps=[s for s, _ in evidence.observed_opponent_commitments],
                **common,
            )
        )

    final = series_final(
        rows, pair, counted=counted, games_played=games_played, first_meeting=first_meeting
    )
    if agreed_rows is not None and agreed_rows != rows:
        raise SelfVerifyError("published result rows differ from the mutually agreed rows")
    if agreed_final is not None and agreed_final != final:
        raise SelfVerifyError("published aggregate differs from the mutually agreed aggregate")
    starts = [json.loads(files[log_name(game_id, n)])["summary"]["started_at"] for n in range(1, 7)]
    ends = [json.loads(files[log_name(game_id, n)])["summary"]["ended_at"] for n in range(1, 7)]
    files[declaration_name(game_id)] = document_bytes(
        build_declaration(
            **ids,
            groups=groups,
            num_sub_games=len(rows), max_tokens_per_game=max_tokens_per_game,
            timezone="Asia/Jerusalem", game_started_at=min(starts), game_ended_at=max(ends),
            step_zero=step_zero, **common,
        )
    )
    files[result_name(game_id)] = document_bytes(
        build_result(
            **ids, groups=list(pair), sub_games=rows, final_result=final,
            mutual_agreement=mutual_agreement(game_id, final, rows, confirmed=confirmed),
            **common,
        )
    )
    return files


def publish_kit_bundle(
    artifact_root: Path | str,
    result: SeriesResult,
    *,
    on_checkpoint: Checkpoint | None = None,
    include_tokens: bool = True,
    **kwargs,
) -> Path:
    """Publish at ``<root>/official/<game_uid>/``, atomically or not at all."""
    from police_peer.reporting.kit_bundle_publish import publish_kit_bundle as publish

    return publish(
        artifact_root, result, on_checkpoint=on_checkpoint,
        include_tokens=include_tokens, **kwargs,
    )
