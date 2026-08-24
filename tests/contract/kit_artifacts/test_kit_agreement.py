"""Agreement is decided on one digest, and silence is never assent."""

from __future__ import annotations

import pytest

from common.transport.kit_agreement import (
    AGREEMENT_KIND,
    NotAgreedError,
    assert_reportable,
    build_proposal,
    evaluate,
    proposal_wire,
)
from common.transport.kit_consensus import consensus_scope, consensus_sha256

GAME_ID, UID = "a-vs-b", "3f2a6b1c-0000-4000-8000-000000000001"
FINAL = {
    "total_score": {"a": 20, "b": 5}, "sub_games_won": {"a": 1, "b": 0}, "ties": 0,
    "winner_group": "a", "series_tie": False,
}
ROWS = [{
    "sub_game_number": 1, "roles": {"a": "police", "b": "thief"}, "result": "capture",
    "winner_group": "a", "score": {"a": 20, "b": 5},
}]


def ours():
    return build_proposal(GAME_ID, UID, FINAL, ROWS)


def theirs(**overrides) -> dict:
    return {**proposal_wire(ours()), **overrides}


def test_the_proposal_digest_is_the_consensus_digest():
    assert ours().consensus_sha256 == consensus_sha256(consensus_scope(GAME_ID, FINAL, ROWS))


def test_matching_digests_agree():
    outcome = evaluate(ours(), theirs())
    assert outcome.agreed
    assert outcome.their_sha == ours().consensus_sha256


def test_differing_digests_do_not_agree_and_the_reason_names_both():
    outcome = evaluate(ours(), theirs(consensus_sha256="f" * 64))
    assert not outcome.agreed
    assert ours().consensus_sha256 in outcome.reason
    assert "f" * 64 in outcome.reason


def test_silence_is_not_assent():
    """A timeout that read as agreement is how one side ends up reporting alone."""
    outcome = evaluate(ours(), None)
    assert not outcome.agreed
    assert "no counter-proposal" in outcome.reason


def test_a_message_of_the_wrong_kind_does_not_agree():
    outcome = evaluate(ours(), theirs(kind="something_else"))
    assert not outcome.agreed
    assert AGREEMENT_KIND in outcome.reason


def test_a_counter_proposal_with_no_digest_does_not_agree():
    proposal = theirs()
    del proposal["consensus_sha256"]
    assert not evaluate(ours(), proposal).agreed


def test_two_uids_for_one_match_never_agree_even_on_a_matching_digest():
    """The contradiction rule 35 zeroes both teams for."""
    outcome = evaluate(ours(), theirs(game_uid="99999999-0000-4000-8000-000000000000"))
    assert not outcome.agreed
    assert "game_uid" in outcome.reason


def test_the_wire_message_carries_the_aggregate_so_a_dispute_is_diffable():
    wire = proposal_wire(ours())
    assert wire["kind"] == AGREEMENT_KIND
    assert wire["final_result"] == FINAL
    assert wire["consensus_sha256"] == ours().consensus_sha256


def test_a_counted_series_without_agreement_refuses_to_report():
    with pytest.raises(NotAgreedError, match="no mutual agreement"):
        assert_reportable(evaluate(ours(), None), counted=True)


def test_a_warm_up_owes_no_report_so_it_never_raises():
    assert_reportable(evaluate(ours(), None), counted=False)


def test_an_agreed_counted_series_is_reportable():
    assert_reportable(evaluate(ours(), theirs()), counted=True)
