"""The settlement exchange: it decides, it waits, and it never raises into a played series."""

from __future__ import annotations

import threading

from common.transport.kit_agreement import build_proposal, evaluate, proposal_wire
from common.transport.loopback import pair
from police_peer.evidence.token_ledger import TokenLedger
from police_peer.wire.result_agreement import exchange, exchange_token_evidence

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


def test_matching_digest_for_wrong_or_missing_game_identifiers_does_not_agree():
    ours = proposal()
    messages = (
        dict(proposal_wire(ours), game_id="wrong-game"),
        {key: value for key, value in proposal_wire(ours).items() if key != "game_id"},
        {key: value for key, value in proposal_wire(ours).items() if key != "game_uid"},
    )
    assert all(not evaluate(ours, message).agreed for message in messages)


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


def test_both_peers_exchange_six_known_zero_token_totals():
    channel_a, channel_b = pair("a", "b")
    outcomes, errors = {}, []

    def go(name, channel, ours, theirs):
        try:
            outcomes[name] = exchange_token_evidence(
                channel, TokenLedger(), game_id=GAME_ID, game_uid=UID,
                our_group=ours, opponent_group=theirs, counted=False, budget=1.0,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [
        threading.Thread(target=go, args=("a", channel_a, "a", "b")),
        threading.Thread(target=go, args=("b", channel_b, "b", "a")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    expected = {number: {"a": 0, "b": 0} for number in range(1, 7)}
    assert outcomes == {"a": expected, "b": expected}
