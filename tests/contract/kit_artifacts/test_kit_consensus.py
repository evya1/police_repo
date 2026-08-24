"""The golden consensus digest -- the assertion that pins the whole settlement contract.

The digest assertion below is the load-bearing one. It is computed from rows in a bundle a
third party published, and it reproduces only if the serialization form, the preimage scope
and the row-key set are all exactly right. Nothing we wrote is on both sides of it.
"""

from __future__ import annotations

import json

from common.transport import kit_consensus as consensus

#: The digest the kit's own published bundle carries. See tests/fixtures/kit_reference/.
GOLDEN_CONSENSUS = "f47666a35230d0327f2136cb425a421c2b9035ab8e97b823d4a7943e69a15dbf"

A, B = "team-aleph", "team-bet"


class Row:
    """A minimal stand-in for a SeriesRow -- the four fields settlement actually reads."""

    def __init__(self, number, role, outcome, steps=6, audit_ok=True):
        from common.domain.scoring import SCORES

        self.sub_game_number = number
        self.role = role
        self.outcome = outcome
        self.steps = steps
        self.audit_ok = audit_ok
        self.score_police, self.score_thief = SCORES[outcome]


def rows_from(kit_result: dict) -> list[dict]:
    """The kit bundle's own rows, trimmed to what our builders produce."""
    return kit_result["sub_games"]


# --- the golden vector ---------------------------------------------------------------------


def test_consensus_digest_reproduces_the_published_signature(kit_result, kit_game_id):
    """Serialization form, preimage scope and row keys, all pinned by one third-party hash."""
    scope = consensus.consensus_scope(kit_game_id, kit_result["final_result"], rows_from(kit_result))
    assert consensus.consensus_sha256(scope) == GOLDEN_CONSENSUS
    assert kit_result["mutual_agreement"]["sha256"] == GOLDEN_CONSENSUS


def test_the_compact_canonical_form_would_not_match(kit_result, kit_game_id):
    """Negative control: the form every OTHER hash in this repo uses is the wrong one here."""
    scope = consensus.consensus_scope(kit_game_id, kit_result["final_result"], rows_from(kit_result))
    import hashlib

    compact = hashlib.sha256(
        json.dumps(scope, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert compact != GOLDEN_CONSENSUS


def test_tie_is_excluded_from_the_row_preimage():
    assert "tie" not in consensus.CONSENSUS_ROW_KEYS
    assert set(consensus.CONSENSUS_ROW_KEYS) == {
        "sub_game_number", "roles", "result", "winner_group", "score"
    }


def test_league_fields_sit_outside_the_signed_aggregate():
    """A per-side claim inside a shared preimage would make agreement impossible."""
    for field in (
        "games_played_including_this", "first_meeting_between_groups",
        "diversity_reward_applied", "tokens_total_series",
    ):
        assert field not in consensus.CONSENSUS_AGGREGATE_KEYS


def test_mutual_agreement_reports_confirmation_honestly(kit_result, kit_game_id):
    rows = kit_result["sub_games"]
    block = consensus.mutual_agreement(kit_game_id, kit_result["final_result"], rows, confirmed=False)
    assert block["sha256"] == GOLDEN_CONSENSUS
    assert block["confirmed"] is False
