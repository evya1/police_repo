"""Two peers on one loopback channel must reach one agreement, byte-identically."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from common.domain.scoring import Role
from common.transport.kit_agreement import build_proposal, proposal_wire
from common.transport.kit_consensus import consensus_scope, consensus_sha256
from common.transport.loopback import pair
from common.transport.series import PeerFacade, SeriesResult
from police_peer.reporting.settlement import settle, settlement_rows
from police_peer.sdk import Budgets, create_peer
from police_peer.wire.result_agreement import exchange

CONFIG = Path(__file__).resolve().parents[2] / "config" / "game.json"
GROUP_A, GROUP_B = "settle-a", "settle-b"


def _run_pair(name_a: str, name_b: str) -> tuple[SeriesResult, SeriesResult, object, object]:
    channel_a, channel_b = pair(name_a, name_b)
    budgets = Budgets(turn_timeout=10.0, connect_timeout=10.0, poll_interval=0.005)
    police = create_peer(CONFIG, channel=channel_a, role=Role.POLICE, group_id=name_a,
                         budgets=budgets)
    thief = create_peer(CONFIG, channel=channel_b, role=Role.THIEF, group_id=name_b,
                        budgets=budgets)
    out: dict[str, SeriesResult] = {}
    errors: list[Exception] = []

    def go(name: str, facade: PeerFacade) -> None:
        try:
            out[name] = facade.run()
        except Exception as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=go, args=("p", police)),
               threading.Thread(target=go, args=("t", thief))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise errors[0]
    return out["p"], out["t"], channel_a, channel_b


@pytest.fixture(scope="module")
def settled_pair():
    return _run_pair(GROUP_A, GROUP_B)


def test_both_peers_reach_agreement_on_a_clean_series(settled_pair):
    p_result, t_result, channel_a, channel_b = settled_pair
    assert p_result.settled and t_result.settled

    outcomes: dict[str, object] = {}

    def settle_one(name, result, channel, our_group):
        outcomes[name] = settle(channel, result, our_group=our_group, budget=2.0)

    threads = [
        threading.Thread(target=settle_one, args=("p", p_result, channel_a, GROUP_A)),
        threading.Thread(target=settle_one, args=("t", t_result, channel_b, GROUP_B)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes["p"].agreed, outcomes["p"].reason
    assert outcomes["t"].agreed, outcomes["t"].reason


def test_both_sides_derive_a_byte_identical_consensus_digest(settled_pair):
    p_result, t_result, _, _ = settled_pair
    p_rows, p_final = settlement_rows(p_result, our_group=GROUP_A)
    t_rows, t_final = settlement_rows(t_result, our_group=GROUP_B)
    p_digest = consensus_sha256(consensus_scope(p_result.game_id, p_final, p_rows))
    t_digest = consensus_sha256(consensus_scope(t_result.game_id, t_final, t_rows))
    assert p_digest == t_digest, "two honest peers must derive one settlement digest"


def test_a_perturbed_side_does_not_agree_and_neither_result_claims_confirmation():
    p_result, t_result, channel_a, channel_b = _run_pair("bad-a", "bad-b")

    # Perturb only the police side's OWN view of its rows before it proposes -- an honest
    # divergence a bug or a lying opponent could produce, never something the wire creates.
    p_rows, p_final = settlement_rows(p_result, our_group="bad-a")
    p_rows[0]["score"] = {"bad-a": 999, "bad-b": 0}
    tampered = build_proposal(p_result.game_id, p_result.game_uid, p_final, p_rows)
    channel_a.send_control(proposal_wire(tampered))

    t_rows, t_final = settlement_rows(t_result, our_group="bad-b")
    honest = build_proposal(t_result.game_id, t_result.game_uid, t_final, t_rows)
    outcome = exchange(channel_b, honest, budget=2.0)

    assert not outcome.agreed
    assert "consensus digests differ" in outcome.reason
