"""Mutual result agreement: agree only on the consensus digest, and never invent a sanction."""

from __future__ import annotations

import json

import pytest

from common.transport.kit_agreement import (
    AGREEMENT_KIND,
    NO_COUNTER_PROPOSAL,
    AgreementProposal,
    NotAgreed,
    assert_reportable,
    build_proposal,
    evaluate,
    proposal_wire,
)
from common.transport.kit_consensus import consensus_scope, consensus_sha256


def _proposal(kit_result: dict, kit_game_id: str) -> AgreementProposal:
    rows = kit_result["sub_games"]
    return build_proposal(kit_game_id, kit_result["game_uid"], kit_result["final_result"], rows)


def test_equal_digests_agree(kit_result, kit_game_id):
    ours = _proposal(kit_result, kit_game_id)
    theirs_wire = proposal_wire(ours)

    outcome = evaluate(ours, theirs_wire)

    assert outcome.agreed is True
    assert outcome.their_sha == ours.consensus_sha256


def test_different_digests_do_not_agree_and_the_reason_names_both(kit_result, kit_game_id):
    ours = _proposal(kit_result, kit_game_id)
    theirs_wire = proposal_wire(ours)
    theirs_wire["consensus_sha256"] = "0" * 64

    outcome = evaluate(ours, theirs_wire)

    assert outcome.agreed is False
    assert ours.consensus_sha256 in outcome.reason
    assert "0" * 64 in outcome.reason
    assert outcome.their_sha == "0" * 64


def test_a_missing_counter_proposal_does_not_agree(kit_result, kit_game_id):
    ours = _proposal(kit_result, kit_game_id)

    outcome = evaluate(ours, None)

    assert outcome.agreed is False
    assert outcome.reason == NO_COUNTER_PROPOSAL
    assert outcome.their_sha is None


def test_a_wrong_kind_message_does_not_agree(kit_result, kit_game_id):
    ours = _proposal(kit_result, kit_game_id)
    wire = proposal_wire(ours)
    wire["kind"] = "not_a_result_agreement"

    outcome = evaluate(ours, wire)

    assert outcome.agreed is False


def test_assert_reportable_raises_on_a_counted_disagreement(kit_result, kit_game_id):
    ours = _proposal(kit_result, kit_game_id)
    outcome = evaluate(ours, None)

    with pytest.raises(NotAgreed):
        assert_reportable(outcome, counted=True)


def test_assert_reportable_is_a_no_op_for_warmup(kit_result, kit_game_id):
    ours = _proposal(kit_result, kit_game_id)
    outcome = evaluate(ours, None)

    assert_reportable(outcome, counted=False)  # must not raise


def test_assert_reportable_is_a_no_op_when_agreed(kit_result, kit_game_id):
    ours = _proposal(kit_result, kit_game_id)
    outcome = evaluate(ours, proposal_wire(ours))

    assert_reportable(outcome, counted=True)  # must not raise


def test_proposal_wire_round_trips_through_the_canonical_serializer(kit_result, kit_game_id):
    ours = _proposal(kit_result, kit_game_id)
    wire = proposal_wire(ours)

    reparsed = json.loads(json.dumps(wire, sort_keys=True, ensure_ascii=False))

    assert reparsed == wire
    assert reparsed["kind"] == AGREEMENT_KIND


def test_build_proposal_derives_the_digest_never_declares_it(kit_result, kit_game_id):
    rows = kit_result["sub_games"]
    proposal = build_proposal(kit_game_id, kit_result["game_uid"], kit_result["final_result"], rows)

    expected_scope = consensus_scope(kit_game_id, kit_result["final_result"], rows)
    assert proposal.consensus_sha256 == consensus_sha256(expected_scope)
