"""Filename grammar and the shared envelope every kit artifact carries (CT-07).

The four submission artifacts take their names from one ``game_id`` and share one
``game_uid`` (book App. F table 20). Per-sub-game files carry a zero-padded ``_g<NN>``;
match-level files never do. Keeping the grammar in one module means the projection in
``kit_documents`` and any future official-schema adapter agree on names by construction
rather than by convention.

The outward documents use the instructor reference's Appendix-F schema version 1.1.
"""

from __future__ import annotations

#: Appendix-F outward schema version from the pinned instructor reference.
SCHEMA_VERSION = "1.1"

_LINKS_REMARK = (
    "match-level files are named <kind>_<game_id>.json; per-sub-game files carry _g<NN>. "
    "All four share one game_uid, which is what joins them."
)


def declaration_name(game_id: str) -> str:
    """Return the match-level declaration filename."""
    return f"declaration_{game_id}.json"


def result_name(game_id: str) -> str:
    """Return the match-level result filename."""
    return f"result_{game_id}.json"


def config_name(game_id: str, sub_game_number: int) -> str:
    """Return the per-sub-game config filename, zero-padded to at least two digits."""
    return f"config_{game_id}_g{sub_game_number:02d}.json"


def log_name(game_id: str, sub_game_number: int) -> str:
    """Return the per-sub-game log filename, zero-padded to at least two digits."""
    return f"log_{game_id}_g{sub_game_number:02d}.json"


def links_block(game_id: str, github: dict | None = None) -> dict:
    """Return the cross-reference block naming all four artifact kinds.

    ``github`` carries the per-group repository links (App. E rule 49) and is omitted
    entirely when the caller does not know them -- an absent link is never invented.
    """
    links = {
        "_remark": _LINKS_REMARK,
        "declaration": declaration_name(game_id),
        "config": f"config_{game_id}_g<NN>.json",
        "log": f"log_{game_id}_g<NN>.json",
        "result": result_name(game_id),
    }
    if github:
        links["github"] = github
    return links


def base_block(game_id: str, game_uid: str, github: dict | None = None) -> dict:
    """Return the envelope every artifact of one match shares."""
    return {
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "game_uid": game_uid,
        "links": links_block(game_id, github),
    }
