"""Pure builders for the four kit submission artifacts (CT-07, ADR-012).

This module is a PROJECTION of evidence that is already sealed. It performs no I/O, reads no
clock, and -- the point of the whole design -- never hashes a game payload. Our internal
records already carry commitments that reproduce under the kit's own construction; the only
thing that ever differed was the SHAPE. So records arrive here already wrapped by
``league_kit_envelope.wrap_outbound_records`` and are passed through untouched.

``config_sha256`` is the one hash computed here, and it is over the negotiated terms rather
than over any game payload -- an identifier for the agreed physics, not a re-commitment.

Nothing is defaulted that a caller might not know. An absent timestamp, commit or opponent
field is OMITTED rather than filled with a placeholder: the kit's checker tolerates unknown
and missing keys, and it does not tolerate a lie. The ``league`` block is the sharpest case --
an armed counted/uncounted marker on a run that was not counted is a false declaration under
App. E rules 37-38, so it is never defaulted, only carried when the caller states it.
"""

from __future__ import annotations

import hashlib

from common.transport.canonical import canonical_bytes
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
    max_tokens_per_game: int | None = None,
    step_zero: dict | None = None,
    league: dict | None = None,
    github: dict | None = None,
) -> dict:
    """Build the pre-game declaration: everything fixed across the series."""
    if len(groups) != 2:
        raise KitDocumentError(f"a declaration names exactly two groups, got {len(groups)}")
    doc = {
        **base_block(game_id, game_uid, github),
        "declaration_type": "pre_game_declaration",
        "report_type": "declaration",
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
    doc = {
        **base_block(game_id, game_uid, github),
        "sub_game_number": sub_game_number,
        "config_name": f"config_{game_id}_g{sub_game_number:02d}.json",
        "terms": terms,
        "config_sha256": _terms_digest(terms),
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
        **base_block(game_id, game_uid, github),
        "sub_game_number": sub_game_number,
        "summary": summary,
        "records": check_records(records, "own"),
    }
    if opponent_records:
        doc["opponent_records"] = check_records(opponent_records, "opponent")
    if opponent_committed_steps is not None:
        doc["opponent_committed_steps"] = sorted(opponent_committed_steps)
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
        **base_block(game_id, game_uid, github),
        "report_type": "final_game_result",
        "groups": list(groups),
        "num_sub_games": len(sub_games),
        "sub_games": sub_games,
        "final_result": final_result,
    }
    if mutual_agreement is not None:
        doc["mutual_agreement"] = mutual_agreement
    return _with_optional(doc, league)
