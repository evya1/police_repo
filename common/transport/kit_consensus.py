"""Canonical digest of the complete official result agreed by both peers."""

from __future__ import annotations

import hashlib
import json

#: Every official result-row field is inside the agreement preimage.
CONSENSUS_ROW_KEYS = (
    "sub_game_number", "roles", "started_at", "ended_at", "result", "winner_group",
    "tie", "steps", "github_commit", "tokens", "score", "log_files", "audit",
)

#: The five aggregate keys inside the consensus preimage.
CONSENSUS_AGGREGATE_KEYS = (
    "total_score", "sub_games_won", "ties", "winner_group", "series_tie",
)


def consensus_scope(game_id: str, final_result: dict, rows: list[dict]) -> dict:
    """Build the complete agreed result preimage."""
    return {
        "game_id": game_id,
        "aggregate": final_result,
        "sub_games": rows,
    }


def consensus_sha256(scope: dict) -> str:
    """Digest the consensus scope in the spaced canonical form. See the module docstring."""
    spaced = json.dumps(scope, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(spaced.encode("utf-8")).hexdigest()


def mutual_agreement(
    game_id: str, final_result: dict, rows: list[dict], *, confirmed: bool
) -> dict:
    """The settlement block: the shared digest, and whether the opponent actually confirmed it.

    ``confirmed`` is never assumed. A result that claims an agreement which did not happen is
    worse than one that admits it is unsettled, because the opponent's report will say so.
    """
    return {
        "sha256": consensus_sha256(consensus_scope(game_id, final_result, rows)),
        "confirmed": bool(confirmed),
    }
