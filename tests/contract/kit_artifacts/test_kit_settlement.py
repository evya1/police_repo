"""Settlement derivation: rows in, aggregate out.

The aggregate is checked against the kit bundle's own declared totals, so the derivation is
pinned to numbers a third party published rather than to our own arithmetic.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Outcome, Role
from common.transport import kit_settlement as settle
from common.transport.kit_settlement import KitSettlementError

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


def test_aggregate_derives_from_the_kit_bundles_own_rows(kit_result):
    derived = settle.series_final(
        kit_result["sub_games"], (A, B), counted=True,
        games_played={A: 1, B: 1}, first_meeting=True,
    )
    declared = kit_result["final_result"]
    for key in ("total_score", "sub_games_won", "ties", "winner_group", "series_tie"):
        assert derived[key] == declared[key], key
    assert derived["diversity_reward_applied"] == declared["diversity_reward_applied"]
    assert derived["total_score"] == {A: 90, B: 30}


# --- derivation rules ----------------------------------------------------------------------


def a_row(number, role, outcome):
    return settle.result_row(
        row=Row(number, role, outcome), our_group=A, opponent_group=B,
        tokens={A: 0, B: 0}, log_file=f"log_g{number:02d}.json",
    )


def test_capture_and_survival_map_onto_the_fixed_table():
    capture = a_row(1, Role.POLICE, Outcome.CAPTURE)
    assert capture["score"] == {A: 20, B: 5}
    assert capture["winner_group"] == A
    survival = a_row(2, Role.THIEF, Outcome.SURVIVAL)
    assert survival["score"] == {A: 10, B: 5}
    assert survival["winner_group"] == A


def test_a_zeroed_row_is_a_sanction_not_a_tie():
    row = a_row(1, Role.POLICE, Outcome.TAMPER_FORFEIT)
    assert row["score"] == {A: 0, B: 0}
    assert row["tie"] is False
    assert row["winner_group"] is None
    assert row["audit"]["tampered"] is True


def test_row_accounting_carries_zeroed_rows_explicitly():
    rows = [
        a_row(1, Role.POLICE, Outcome.CAPTURE),
        a_row(2, Role.THIEF, Outcome.SURVIVAL),
        a_row(3, Role.POLICE, Outcome.TECHNICAL_LOSS),
    ]
    final = settle.series_final(rows, (A, B), counted=True)
    assert final["sub_games_won"][A] == 2
    assert final["sub_games_won"][B] == 0
    assert final["ties"] == 0
    assert final["total_score"] == {A: 30, B: 10}


def test_a_level_series_adds_the_tie_score_to_each_side():
    rows = [a_row(1, Role.POLICE, Outcome.CAPTURE), a_row(2, Role.POLICE, Outcome.CAPTURE)]
    rows[1]["score"] = {A: 5, B: 20}
    rows[1]["winner_group"] = B
    final = settle.series_final(rows, (A, B), counted=True)
    assert final["series_tie"] is True
    assert final["winner_group"] is None
    assert final["total_score"] == {A: 27, B: 27}
    assert final["tie_score_each"] == settle.TIE_SCORE


def test_no_diversity_reward_is_awarded_on_a_tie_or_to_a_loser():
    rows = [a_row(1, Role.POLICE, Outcome.CAPTURE)]
    final = settle.series_final(rows, (A, B), counted=True, first_meeting=True)
    assert final["diversity_reward_applied"] == {A: True, B: False}
    assert final["total_score"] == {A: 20, B: 5}, "the +10 never enters the totals"


def test_a_warm_up_never_arms_the_league_fields():
    rows = [a_row(1, Role.POLICE, Outcome.CAPTURE)]
    final = settle.series_final(rows, (A, B), counted=False, first_meeting=True)
    assert final["diversity_reward_applied"] == {A: False, B: False}


def test_an_unclaimed_opponent_count_is_null_never_zero():
    rows = [a_row(1, Role.POLICE, Outcome.CAPTURE)]
    final = settle.series_final(rows, (A, B), counted=True, games_played={A: 3, B: None})
    assert final["games_played_including_this"] == {A: 3, B: None}


def test_tokens_total_is_the_sum_of_the_rows():
    rows = [a_row(1, Role.POLICE, Outcome.CAPTURE), a_row(2, Role.THIEF, Outcome.SURVIVAL)]
    rows[0]["tokens"] = {A: 120, B: 0}
    rows[1]["tokens"] = {A: 80, B: 0}
    final = settle.series_final(rows, (A, B), counted=True)
    assert final["tokens_total_series"] == {A: 200, B: 0}


def test_a_winner_outside_the_pair_is_refused_not_crashed_on():
    rows = [a_row(1, Role.POLICE, Outcome.CAPTURE)]
    rows[0]["winner_group"] = "nobody-here"
    with pytest.raises(KitSettlementError, match="not one of"):
        settle.series_final(rows, (A, B), counted=True)


def test_a_malformed_score_map_is_refused_not_summed():
    rows = [a_row(1, Role.POLICE, Outcome.CAPTURE)]
    rows[0]["score"] = 20
    with pytest.raises(KitSettlementError, match="per-group map"):
        settle.series_final(rows, (A, B), counted=True)


def test_a_row_claiming_a_tie_its_scores_contradict_is_refused():
    rows = [dict(a_row(1, Role.POLICE, Outcome.CAPTURE), winner_group=None)]
    with pytest.raises(KitSettlementError, match="wins exactly when"):
        settle.series_final(rows, (A, B), counted=True)


def test_a_row_naming_the_losing_side_as_winner_is_refused():
    rows = [dict(a_row(1, Role.POLICE, Outcome.CAPTURE), winner_group=B)]
    with pytest.raises(KitSettlementError, match="did not score highest"):
        settle.series_final(rows, (A, B), counted=True)


def test_zeroed_rows_are_counted_apart_from_ties():
    """The naive won+won+ties identity fails any series with a technical loss."""
    rows = [
        a_row(1, Role.POLICE, Outcome.CAPTURE),
        a_row(2, Role.POLICE, Outcome.TIMEOUT),
    ]
    final = settle.series_final(rows, (A, B), counted=True)
    assert final["ties"] == 0, "a zeroed row is a sanction, not a tie"
    assert final["sub_games_won"] == {A: 1, B: 0}
