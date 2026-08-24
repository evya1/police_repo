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

from common.transport.atomic_publish import Checkpoint, SelfVerifyError, publish_atomic
from common.transport.canonical import commit as recompute_commit
from common.transport.kit_consensus import mutual_agreement
from common.transport.kit_documents import (
    build_config,
    build_declaration,
    build_log,
    build_result,
)
from common.transport.kit_names import config_name, declaration_name, log_name, result_name
from common.transport.kit_records import build_summary
from common.transport.kit_settlement import result_row, series_final
from common.transport.league_kit_envelope import wrap_outbound_records
from common.transport.series import SeriesResult

#: The kit reads one flat directory; the internal bundle keeps its own place beside this one.
KIT_SUBDIR = "kit"


def _records(sealed) -> list[dict]:
    """Decode our sealed records back to dicts and wrap them in the kit's audit envelope."""
    flat = [
        {**json.loads(record.payload_bytes), "nonce": record.nonce, "commit": record.commitment}
        for record in sealed
    ]
    return wrap_outbound_records(flat)


def _document_bytes(doc: dict) -> bytes:
    """Readable bytes with an explicit newline -- the EMAILED report is the compact form."""
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _audit_block(evidence, row) -> dict:
    return {
        "passed": bool(row.audit_ok),
        "skipped": False,
        "verified_steps": len(evidence.own_records),
        "failed_steps": [],
    }


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
) -> dict[str, bytes]:
    """Build the 14 kit documents for one settled series. Pure: no I/O, no clock."""
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
        files[config_name(game_id, number)] = _document_bytes(
            build_config(**ids, sub_game_number=number, terms=terms, **common)
        )
        entry = result_row(
            row=row, our_group=ours, opponent_group=theirs,
            tokens=(tokens_by_sub_game or {}).get(number, {ours: 0, theirs: 0}),
            log_file=log_name(game_id, number),
        )
        rows.append(entry)
        summary = build_summary(
            sub_game_number=number, our_group=ours, our_role=row.role.value,
            opponent_group=theirs, result=row.outcome.value,
            winner_group=entry["winner_group"], steps=row.steps,
            audit=_audit_block(evidence, row),
        )
        files[log_name(game_id, number)] = _document_bytes(
            build_log(
                **ids, sub_game_number=number, summary=summary,
                records=_records(evidence.own_records),
                opponent_records=(
                    _records(evidence.opponent_records) if evidence.opponent_records else None
                ),
                opponent_committed_steps=[s for s, _ in evidence.observed_opponent_commitments],
                **common,
            )
        )

    final = series_final(
        rows, pair, counted=counted, games_played=games_played, first_meeting=first_meeting
    )
    files[declaration_name(game_id)] = _document_bytes(
        build_declaration(
            **ids,
            groups=groups or [{"group_id": pair[0]}, {"group_id": pair[1]}],
            num_sub_games=len(rows), max_tokens_per_game=max_tokens_per_game,
            step_zero=step_zero, **common,
        )
    )
    files[result_name(game_id)] = _document_bytes(
        build_result(
            **ids, groups=list(pair), sub_games=rows, final_result=final,
            mutual_agreement=mutual_agreement(game_id, final, rows, confirmed=confirmed),
            **common,
        )
    )
    return files


def _self_verify(staging: Path) -> None:
    """Reload every written log and reproduce every commit before anything is published."""
    problems: list[str] = []
    for path in sorted(staging.glob("log_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for half in ("records", "opponent_records"):
            for index, record in enumerate(doc.get(half) or []):
                recomputed = recompute_commit(record["payload"], record["nonce"])
                if recomputed != record["commit"]:
                    problems.append(f"{path.name} {half}[{index}] does not reproduce its commit")
    if problems:
        raise SelfVerifyError("; ".join(problems[:6]))


def publish_kit_bundle(
    artifact_root: Path | str,
    result: SeriesResult,
    *,
    on_checkpoint: Checkpoint | None = None,
    **kwargs,
) -> Path:
    """Publish the kit bundle at ``<root>/kit/<game_uid>/``, atomically or not at all."""
    files = build_kit_bundle(result, **kwargs)
    return publish_atomic(
        Path(artifact_root) / KIT_SUBDIR, result.game_uid, files, _self_verify,
        on_checkpoint=on_checkpoint,
    )
