"""Tests for T034 per-subgame replay evidence capture (RP-06, OBS-006, SEC-005/006)."""

from __future__ import annotations

import json

from common.domain.scoring import Outcome, Role
from common.transport.canonical import commit as hash_commit
from common.transport.loopback import pair
from common.transport.replay_evidence import SubgameReplayEvidence, capture_subgame_evidence
from common.transport.series import PeerConfig, SeriesRow, run_series
from police_peer.wire import StandInEngine


class DummyBudgets:
    """Minimal budgets implementation for testing."""

    turn_timeout = 10.0
    connect_timeout = 10.0
    poll_interval = 0.005


_TERMS = {
    "board_size": 7,
    "smell_grid_size": 5,
    "decay_per_step": 0.1,
    "emit_intensity": 0.9,
    "min_center_intensity": 0.5,
    "max_steps": 35,
    "barriers_max": 14,
    "setting": "New York",
    "hint_max_words": 15,
    "axis_origin_corner": "top-left",
    "axis_start_index": 0,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
    "num_games": 6,
}


def _run_pair():
    """Run a full six-sub-game series over loopback (mirrors test_series.py)."""
    a, b = pair("A", "B")
    config_a = PeerConfig(natural_role=Role.POLICE, budgets=DummyBudgets(), terms=_TERMS)
    config_b = PeerConfig(natural_role=Role.THIEF, budgets=DummyBudgets(), terms=_TERMS)
    return run_series(a, b, config_a, config_b, StandInEngine(Role.POLICE), StandInEngine(Role.THIEF))


def _rehashes(record) -> bool:
    """True when re-canonicalizing + re-hashing the sealed record matches its commitment."""
    payload = json.loads(record.payload_bytes)
    return hash_commit(payload, record.nonce) == record.commitment


def _dummy_row(outcome: Outcome = Outcome.CAPTURE, audit_ok: bool = True) -> SeriesRow:
    return SeriesRow(
        sub_game_number=1, role=Role.POLICE, outcome=outcome, steps=0,
        score_police=0, score_thief=0, audit_ok=audit_ok,
    )


class TestSixOrderedEntriesAccumulate:
    """SeriesResult.replay_evidence accumulates six ordered entries per side."""

    def test_six_entries_in_subgame_order_with_identity_attached(self) -> None:
        result_a, result_b = _run_pair()
        assert len(result_a.replay_evidence) == 6
        assert len(result_b.replay_evidence) == 6
        assert [e.sub_game_index for e in result_a.replay_evidence] == [1, 2, 3, 4, 5, 6]
        for evidence in result_a.replay_evidence:
            assert isinstance(evidence, SubgameReplayEvidence)
            assert evidence.game_id == result_a.game_id
            assert evidence.game_uid == result_a.game_uid

    def test_row_and_outcomes_identical_to_the_plain_ledger(self) -> None:
        """Evidence capture is a pure observation: it must not change any outcome."""
        result_a, _ = _run_pair()
        for row, evidence in zip(result_a.ledger, result_a.replay_evidence, strict=True):
            assert evidence.row == row
            assert evidence.our_result_claim == row.outcome.value


class TestBothHalvesRehash:
    """Step zero leads both halves; every sealed record re-hashes to its commitment."""

    def test_step_zero_first_and_every_record_rehashes(self) -> None:
        result_a, _ = _run_pair()
        for evidence in result_a.replay_evidence:
            assert evidence.own_records[0].step == 0
            assert evidence.opponent_records[0].step == 0
            for record in (*evidence.own_records, *evidence.opponent_records):
                assert _rehashes(record)


class TestObservedCommitmentsBindOpponentReveals:
    """The Inbox.played snapshot must match the opponent's own revealed commitments."""

    def test_observed_commitments_match_opponent_reveal(self) -> None:
        result_a, _ = _run_pair()
        for evidence in result_a.replay_evidence:
            assert evidence.observed_opponent_commitments
            revealed = {r.step: r.commitment for r in evidence.opponent_records}
            for step, observed_commit in evidence.observed_opponent_commitments:
                assert revealed[step] == observed_commit


class TestAliasMutationCannotChangeEvidence:
    """Mutating a caller-owned input after capture must not reach the sealed evidence."""

    def test_mutating_the_commitments_mapping_after_capture_does_not_leak(self) -> None:
        commitments = {1: "a" * 64, 2: "b" * 64}
        evidence = capture_subgame_evidence(
            sub_game_index=1, terms={}, own_records_raw=[], opponent_records_raw=[],
            observed_opponent_commitments=commitments, our_result_claim="capture",
            opponent_result_claim=None, row=_dummy_row(),
        )
        commitments[1] = "z" * 64
        commitments[3] = "c" * 64
        assert evidence.observed_opponent_commitments == ((1, "a" * 64), (2, "b" * 64))


class TestCaptureNeverCrashesOnHostileInput:
    """A malformed opponent audit must decode-and-report, never raise, into a live game."""

    def test_malformed_opponent_records_are_reported_not_raised(self) -> None:
        evidence = capture_subgame_evidence(
            sub_game_index=1, terms={}, own_records_raw=[],
            opponent_records_raw=[{"not": "a valid record"}],
            observed_opponent_commitments={}, our_result_claim="capture",
            opponent_result_claim=None, row=_dummy_row(audit_ok=False),
        )
        assert evidence.opponent_records == ()
        assert evidence.capture_issues

    def test_non_list_opponent_records_are_reported_not_raised(self) -> None:
        evidence = capture_subgame_evidence(
            sub_game_index=1, terms={}, own_records_raw=[],
            opponent_records_raw="not-a-list",
            observed_opponent_commitments={}, our_result_claim="capture",
            opponent_result_claim=None, row=_dummy_row(audit_ok=False),
        )
        assert evidence.opponent_records == ()
        assert evidence.capture_issues
