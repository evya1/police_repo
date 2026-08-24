"""A real two-sided exchange over the loopback control channel (CT-08, W2-P5)."""

from __future__ import annotations

import copy
import threading

from common.domain.scoring import SCORES, Outcome, Role
from common.transport.kit_agreement import AgreementOutcome, build_proposal
from common.transport.kit_consensus import mutual_agreement
from common.transport.kit_settlement import result_row, series_final
from common.transport.loopback import pair
from police_peer.wire.result_agreement import exchange

GAME_ID = "team-a-vs-team-b"
GAME_UID = "11111111-1111-1111-1111-111111111111"
GROUPS = ("team-a", "team-b")


class _Row:
    def __init__(self, number: int, role: Role, outcome: Outcome, steps: int = 6):
        self.sub_game_number = number
        self.role = role
        self.outcome = outcome
        self.steps = steps
        self.audit_ok = True
        self.score_police, self.score_thief = SCORES[outcome]


def _rows_and_final() -> tuple[list[dict], dict]:
    ledger = [
        _Row(1, Role.POLICE, Outcome.CAPTURE),
        _Row(2, Role.THIEF, Outcome.SURVIVAL),
    ]
    rows = [
        result_row(
            row=r, our_group="team-a", opponent_group="team-b",
            tokens={"team-a": 0, "team-b": 0}, log_file=f"log_{GAME_ID}_g{r.sub_game_number:02d}.json",
        )
        for r in ledger
    ]
    final = series_final(rows, GROUPS, counted=False)
    return rows, final


def _exchange_both(
    rows_a: list[dict], final_a: dict, rows_b: list[dict], final_b: dict
) -> tuple[AgreementOutcome, AgreementOutcome]:
    ours = build_proposal(GAME_ID, GAME_UID, final_a, rows_a)
    theirs = build_proposal(GAME_ID, GAME_UID, final_b, rows_b)

    channel_a, channel_b = pair("A", "B")
    out: dict[str, AgreementOutcome] = {}

    def go(name: str, channel, proposal) -> None:
        out[name] = exchange(channel, proposal, budget=2.0)

    threads = [
        threading.Thread(target=go, args=("a", channel_a, ours)),
        threading.Thread(target=go, args=("b", channel_b, theirs)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out["a"], out["b"]


def test_matching_rows_both_reach_agreement_with_the_same_digest() -> None:
    rows, final = _rows_and_final()
    outcome_a, outcome_b = _exchange_both(rows, final, copy.deepcopy(rows), copy.deepcopy(final))

    assert outcome_a.agreed is True
    assert outcome_b.agreed is True
    assert outcome_a.their_sha == outcome_b.their_sha

    sha_a = mutual_agreement(GAME_ID, final, rows, confirmed=outcome_a.agreed)["sha256"]
    sha_b = mutual_agreement(GAME_ID, final, rows, confirmed=outcome_b.agreed)["sha256"]
    assert sha_a == sha_b


def test_perturbed_rows_on_one_side_reach_no_agreement_on_either_side() -> None:
    rows, final = _rows_and_final()
    perturbed_rows, perturbed_final = _rows_and_final()
    perturbed_rows[0]["score"] = {"team-a": 999, "team-b": 5}

    outcome_a, outcome_b = _exchange_both(rows, final, perturbed_rows, perturbed_final)

    assert outcome_a.agreed is False
    assert outcome_b.agreed is False
    result_a = mutual_agreement(GAME_ID, final, rows, confirmed=outcome_a.agreed)
    result_b = mutual_agreement(GAME_ID, perturbed_final, perturbed_rows, confirmed=outcome_b.agreed)
    assert result_a["confirmed"] is False
    assert result_b["confirmed"] is False
