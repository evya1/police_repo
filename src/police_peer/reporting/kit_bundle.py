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

#: The kit reads one flat directory; the internal bundle keeps its own place beside this one.
KIT_SUBDIR = "kit"


def build_kit_bundle(
    result: SeriesResult,
    *,
    our_group: str,
    counted: bool,
    groups: list[dict] | None = None,
    step_zero: dict | None = None,
    github: dict | None = None,
    league: dict | None = None,
    max_tokens_per_game: int | None = None,
    tokens_by_sub_game: dict[int, dict[str, int]] | None = None,
    games_played: dict[str, int | None] | None = None,
    first_meeting: bool = True,
    confirmed: bool = False,
    include_tokens: bool = True,
) -> dict[str, bytes]:
    """Build the 14 kit documents for one settled series. Pure: no I/O, no clock.

    ``include_tokens`` controls whether the optional per-row ``tokens``` and
    ``final_result.tokens_total_series`` are projected. The kit's checker treats those as
    optional (it skips their sum gate when they are absent), so ``include_tokens=False``
    keeps the kit to only its mandatory fields. The signed aggregate/mutual-agreement are
    computed over the same written rows/final for consistency.
    """
    ours, theirs = our_group, result.opponent_group_id
    if not ours or not theirs:
        raise SelfVerifyError(
            "no opponent group id on the series result, so no per-group projection is possible "
            "-- the greeting must have resolved before a bundle is built"
        )
    pair = tuple(sorted([ours, theirs]))
    game_id, uid = result.game_id, result.game_uid
    ids = {"game_id": game_id, "game_uid": uid}
    common = {"league": league, "github": github}

    files: dict[str, bytes] = {}
    rows: list[dict] = []
    by_number = {row.sub_game_number: row for row in result.ledger}

    for evidence in sorted(result.replay_evidence, key=lambda e: e.sub_game_index):
        number = evidence.sub_game_index
        row = by_number[number]
        terms = json.loads(evidence.terms_bytes)
        files[config_name(game_id, number)] = document_bytes(
            build_config(**ids, sub_game_number=number, terms=terms, **common)
        )
        entry = result_row(
            row=row, our_group=ours, opponent_group=theirs,
            tokens=(tokens_by_sub_game or {}).get(number, {ours: 0, theirs: 0})
            if include_tokens else {ours: 0, theirs: 0},
            log_file=log_name(game_id, number),
        )
        rows.append(entry)
        log_summary = summary(
            evidence, row, number=number, ours=ours, theirs=theirs,
            winner=entry["winner_group"],
        )
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
    written_rows = rows
    written_final = final
    if not include_tokens:
        # Keep the kit to only its mandatory fields: the per-row `tokens` and the
        # aggregate `tokens_total_series` are optional to the kit and dropped here.
        # The consensus digest ignores tokens, so the mutual-agreement is unchanged.
        written_rows = [
            {k: v for k, v in row.items() if k != "tokens"} for row in rows
        ]
        written_final = {k: v for k, v in final.items() if k != "tokens_total_series"}
    files[declaration_name(game_id)] = document_bytes(
        build_declaration(
            **ids,
            groups=groups or [{"group_id": pair[0]}, {"group_id": pair[1]}],
            num_sub_games=len(rows), max_tokens_per_game=max_tokens_per_game,
            step_zero=step_zero, **common,
        )
    )
    files[result_name(game_id)] = document_bytes(
        build_result(
            **ids, groups=list(pair), sub_games=written_rows,
            final_result=written_final,
            mutual_agreement=mutual_agreement(game_id, written_final, written_rows, confirmed=confirmed),
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
    """Publish the kit bundle at ``<root>/kit/<game_uid>/``, atomically or not at all.

    ``include_tokens`` is forwarded to :func:`build_kit_bundle`; when False the kit
    carries only its mandatory fields (no optional token metadata).
    """
    from police_peer.reporting.kit_bundle_publish import publish_kit_bundle as publish

    return publish(
        artifact_root, result, on_checkpoint=on_checkpoint,
        include_tokens=include_tokens, **kwargs,
    )
