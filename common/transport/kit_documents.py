"""Pure builders for the four kit submission artifacts (CT-07, ADR-012).

This pure projection receives already sealed evidence and never re-hashes a game payload.
Records arrive wrapped by ``league_kit_envelope.wrap_outbound_records`` and pass through.

``config_sha256`` is the one hash computed here, and it is over the negotiated terms rather
than over any game payload -- an identifier for the agreed physics, not a re-commitment.

Mandatory evidence is never defaulted. The optional ``league`` block is carried only when
the caller explicitly declares it.
"""

from __future__ import annotations

import hashlib
import json

from common.transport.canonical import canonical_bytes
from common.transport.kit_artifact_schemas import (
    CONFIG_SCHEMA,
    DECLARATION_SCHEMA,
    LOG_SCHEMA,
    RESULT_SCHEMA,
)
from common.transport.kit_names import base_block
from common.transport.kit_records import KitDocumentError, build_summary, check_records

__all__ = [
    "KitDocumentError", "build_config", "build_declaration", "build_log", "build_result",
    "build_summary",
]


def _terms_digest(terms: dict) -> str:
    """Canonical hash of the negotiated terms -- the config artifact's own identifier."""
    return hashlib.sha256(canonical_bytes(terms)).hexdigest()


def _with_optional(doc: dict, league: dict | None) -> dict:
    """Attach the league posture block only when the caller actually declared one."""
    if league is not None:
        doc["league"] = league
    return doc


def build_declaration(
    *,
    game_id: str,
    game_uid: str,
    groups: list[dict],
    num_sub_games: int,
    timezone: str,
    game_started_at: str,
    game_ended_at: str,
    max_tokens_per_game: int | None = None,
    step_zero: dict | None = None,
    league: dict | None = None,
    github: dict | None = None,
) -> dict:
    """Build the pre-game declaration: everything fixed across the series."""
    if len(groups) != 2:
        raise KitDocumentError(f"a declaration names exactly two groups, got {len(groups)}")
    doc = {
        "_schema": DECLARATION_SCHEMA,
        **base_block(game_id, game_uid, github),
        "declaration_type": "pre_game_declaration",
        "timezone": timezone,
        "game_started_at": game_started_at,
        "game_ended_at": game_ended_at,
        "num_sub_games": num_sub_games,
        "groups": {"group_1": groups[0], "group_2": groups[1]},
    }
    if max_tokens_per_game is not None:
        doc["max_tokens_per_game"] = max_tokens_per_game
    if step_zero is not None:
        doc["step_zero"] = step_zero
    return _with_optional(doc, league)


def build_config(
    *,
    game_id: str,
    game_uid: str,
    sub_game_number: int,
    terms: dict,
    league: dict | None = None,
    github: dict | None = None,
) -> dict:
    """Build one sub-game's config: the flat negotiated terms, inline and digested.

    Carrying the terms inline is what lets a checker RE-DERIVE the game_uid rather than merely
    confirm it is self-consistent -- the failure mode a uid built from a wider object survives.
    """
    shared = {k: v for k, v in terms.items() if k not in {
        "_schema", "schema_version", "game_id", "game_uid", "sub_game_number",
        "links", "config_name", "config_sha256",
    }}
    doc = {
        "_schema": CONFIG_SCHEMA,
        **shared,
        **base_block(game_id, game_uid, github),
        "sub_game_number": sub_game_number,
        "config_name": f"config_{game_id}_g{sub_game_number:02d}.json",
        "config_sha256": _terms_digest(shared),
    }
    return _with_optional(doc, league)


def build_log(
    *,
    game_id: str,
    game_uid: str,
    sub_game_number: int,
    summary: dict,
    records: list[dict],
    opponent_records: list[dict] | None = None,
    opponent_committed_steps: list[int] | None = None,
    league: dict | None = None,
    github: dict | None = None,
) -> dict:
    """Build one sub-game's log from records that are ALREADY sealed and wrapped."""
    doc = {
        "_schema": LOG_SCHEMA,
        **base_block(game_id, game_uid, github),
        "summary": summary,
        "records": check_records(records, "own"),
    }
    if opponent_records:
        doc["opponent_records"] = check_records(opponent_records, "opponent")
    if opponent_committed_steps is not None:
        doc["opponent_committed_steps"] = sorted(opponent_committed_steps)
    doc["mutual_agreement"] = {
        "opponent_group_id": summary["opponent_group_id"],
        "sha256": hashlib.sha256(
            json.dumps(doc["records"], sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "confirmed": bool(summary.get("audit", {}).get("passed")),
    }
    return _with_optional(doc, league)


def build_result(
    *,
    game_id: str,
    game_uid: str,
    groups: list[str],
    sub_games: list[dict],
    final_result: dict,
    mutual_agreement: dict | None = None,
    league: dict | None = None,
    github: dict | None = None,
) -> dict:
    """Build the final series result -- the one artifact that is emailed."""
    doc = {
        "_schema": RESULT_SCHEMA,
        **base_block(game_id, game_uid, github),
        "report_type": "final_game_result",
        "timezone": "Asia/Jerusalem",
        "groups": list(groups),
        "num_sub_games": len(sub_games),
        "sub_games": sub_games,
        "final_result": final_result,
    }
    if mutual_agreement is not None:
        doc["mutual_agreement"] = mutual_agreement
    return _with_optional(doc, league)
