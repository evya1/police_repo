"""The settlement consensus digest -- the release's SECOND canonical form (CT-07, ADR-012).

This module exists to be the ONLY place in the repository that serializes with json.dumps'
DEFAULT (spaced) separators. Everything else we hash -- commits, terms signatures, game uids,
config digests -- goes through the compact form in ``common.transport.canonical``, and that
function must never reach this preimage. A peer that signs the compact form produces a digest
that cannot match its opponent's at the exact moment both sides must agree on a result, and
the mismatch looks like a disagreement about the game rather than about a separator.

Keeping the two forms in two modules, under two names, with neither reachable from the other,
is that rule expressed in code rather than remembered.

The PREIMAGE is a second, independent choice, and the wrong one can never match either. The
scope is the aggregate both peers must agree on plus the trimmed rows -- and nothing either
side may legitimately differ on. The league fields (game counts, first-meeting, diversity) sit
OUTSIDE it deliberately: a game count is each team's own unverifiable claim, and a per-side
value inside a shared preimage makes agreement impossible by construction.

``tie`` is likewise absent from the row keys. It lives in the document row and outside the
hash: it is derivable (``winner_group is None``) and the tie COUNT already sits in the signed
aggregate, so the trim loses nothing -- and a six-key row matches nothing that was ever played.
"""

from __future__ import annotations

import hashlib
import json

#: The five row keys inside the consensus preimage.
CONSENSUS_ROW_KEYS = ("sub_game_number", "roles", "result", "winner_group", "score")

#: The five aggregate keys inside the consensus preimage.
CONSENSUS_AGGREGATE_KEYS = (
    "total_score", "sub_games_won", "ties", "winner_group", "series_tie",
)


def consensus_scope(game_id: str, final_result: dict, rows: list[dict]) -> dict:
    """Build the exact preimage two peers must both produce."""
    return {
        "game_id": game_id,
        "aggregate": {k: final_result[k] for k in CONSENSUS_AGGREGATE_KEYS},
        "sub_games": [{k: r[k] for k in CONSENSUS_ROW_KEYS} for r in rows],
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
