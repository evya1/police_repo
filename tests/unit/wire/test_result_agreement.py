"""The settlement exchange: it decides, it waits, and it never raises into a played series."""

from __future__ import annotations

from common.transport.kit_agreement import build_proposal, proposal_wire
from common.transport.loopback import pair
from police_peer.wire.result_agreement import exchange

GAME_ID, UID = "a-vs-b", "3f2a6b1c-0000-4000-8000-000000000001"
FINAL = {
    "total_score": {"a": 20, "b": 5}, "sub_games_won": {"a": 1, "b": 0}, "ties": 0,
    "winner_group": "a", "series_tie": False,
}
ROWS = [{
    "sub_game_number": 1, "roles": {"a": "police", "b": "thief"}, "result": "capture",
    "winner_group": "a", "score": {"a": 20, "b": 5},
}]


def proposal(final=FINAL, rows=ROWS):
    return build_proposal(GAME_ID, UID, final, rows)


def test_two_peers_that_settled_the_same_series_agree():
    ours, theirs = pair("a", "b")
    theirs.send_control(proposal_wire(proposal()))
    outcome = exchange(ours, proposal(), budget=1.0)
    assert outcome.agreed, outcome.reason


def test_two_peers_that_settled_differently_do_not_agree():
    ours, theirs = pair("a", "b")
    other = dict(FINAL, total_score={"a": 5, "b": 20}, winner_group="b")
    theirs.send_control(proposal_wire(build_proposal(GAME_ID, UID, other, ROWS)))
    outcome = exchange(ours, proposal(), budget=1.0)
    assert not outcome.agreed
    assert "consensus digests differ" in outcome.reason


def test_a_silent_opponent_times_out_to_non_agreement():
    ours, _ = pair("a", "b")
    outcome = exchange(ours, proposal(), budget=0.2)
    assert not outcome.agreed
    assert "did not arrive" in outcome.reason
    assert "not assent" in outcome.reason


def test_unrelated_control_traffic_is_skipped_not_mistaken_for_a_settlement():
    ours, theirs = pair("a", "b")
    theirs.send_control({"kind": "something_else", "note": "not a settlement"})
    theirs.send_control(proposal_wire(proposal()))
    assert exchange(ours, proposal(), budget=1.0).agreed


def test_a_send_fault_never_raises_into_a_played_series():
    class Broken:
        def send_control(self, message):
            raise RuntimeError("tunnel died")

    outcome = exchange(Broken(), proposal(), budget=0.2)
    assert not outcome.agreed
    assert "could not be sent" in outcome.reason


def test_a_read_fault_never_raises_into_a_played_series():
    class Broken:
        def send_control(self, message):
            return {"ok": True}

        def poll_control(self):
            raise RuntimeError("socket reset")

    outcome = exchange(Broken(), proposal(), budget=0.2)
    assert not outcome.agreed
    assert "could not be read" in outcome.reason
