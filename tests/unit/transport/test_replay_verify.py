"""Tests for the pure replay verifier (replay.py).

TC-RP-02..05, 08, 10 adapted to the new pure ``verify_replay(log_doc, config_doc)`` API.
Eight tests that failed under the old first-record heuristic now pass under strict decoding.
"""

from __future__ import annotations

import json

import pytest

from common.transport.replay import verify_replay
from common.transport.replay_types import ReplayVerdict
from tests.unit.transport.replay_fixtures import (
    GAME_ID,
    GAME_UID,
    barrier_quota,
    honest_steps,
    jump_step,
    make_config_doc,
    make_log_doc,
    middle_gap_log_doc,
    nested,
    off_board,
    role_wrong_capture_claim,
    seal,
    steps_with_step_values,
    verdict_of,
)


# INCOMPLETE: absent required evidence
def test_no_records_incomplete() -> None:
    assert verdict_of(make_log_doc([])) == ReplayVerdict.INCOMPLETE


def test_missing_terms_incomplete() -> None:
    cfg = make_config_doc()
    del cfg["terms"]
    assert verdict_of(make_log_doc(honest_steps(1)), cfg) == ReplayVerdict.INCOMPLETE


# INVALID: malformed syntax, type, identity, or mixed shape
def test_malformed_commitment_invalid() -> None:
    own = honest_steps(1)
    own[1]["commit"] = "not-64-hex"
    assert verdict_of(make_log_doc(own)) == ReplayVerdict.INVALID


def test_mixed_shape_invalid() -> None:
    own = [seal({"step": 0, "sender": "thief"}), nested({"step": 1, "sender": "thief"})]
    assert verdict_of(make_log_doc(own)) == ReplayVerdict.INVALID


@pytest.mark.parametrize(
    ("label", "steps"),
    [
        ("duplicate", [0, 1, 1, 2]),
        ("skipped", [0, 1, 3]),
        ("negative", [0, -1, 2]),
        ("out_of_order", [0, 2, 1, 3]),
    ],
)
def test_broken_sequence_invalid(label: str, steps: list[int]) -> None:
    own = steps_with_step_values(steps)
    assert verdict_of(make_log_doc(own)) == ReplayVerdict.INVALID


def test_missing_step_zero_invalid() -> None:
    """Real bundles are built by audit_payload, which always prepends step 0 (T034/T046)."""
    own = steps_with_step_values([1, 2, 3])
    report = verify_replay(make_log_doc(own), make_config_doc())
    assert report.verdict == ReplayVerdict.INVALID
    assert any(i.code == "skipped_step" and "0" in i.message for i in report.issues)


def test_wrong_config_game_id_invalid() -> None:
    own = honest_steps(1)
    cfg = make_config_doc(game_id="different-game")
    assert verify_replay(make_log_doc(own), cfg).verdict == ReplayVerdict.INVALID


def test_wrong_uid_invalid() -> None:
    own = honest_steps(1)
    cfg = make_config_doc(game_uid="11111111-2222-3333-4444-555566667777")
    assert verify_replay(make_log_doc(own), cfg).verdict == ReplayVerdict.INVALID


# TAMPERED: commitment mismatch
def test_semantic_payload_mutation_tampered() -> None:
    own = honest_steps(3)
    own[2]["move"] = "MOVE:W"  # stale commit left untouched
    report = verify_replay(make_log_doc(own), make_config_doc())
    assert report.verdict == ReplayVerdict.TAMPERED and any(i.step == 2 for i in report.issues)


# VERIFIED_OK: both halves, checked_records count, canonical formatting insensitivity
def test_both_halves_verified_ok() -> None:
    own = honest_steps(3, sender="thief", intent="evade", start=(3, 3))
    opp = honest_steps(2, sender="police", intent="chase", start=(0, 0))
    report = verify_replay(make_log_doc(own, opp), make_config_doc())
    assert (report.verdict, report.checked_records) == (ReplayVerdict.VERIFIED_OK, 7)


def test_canonical_whitespace_and_key_order_do_not_affect_verification() -> None:
    own = honest_steps(2)
    log = make_log_doc(own)
    cfg = make_config_doc()
    reordered_log = json.loads(json.dumps(log, indent=4, sort_keys=False))
    reordered_cfg = json.loads(json.dumps({k: cfg[k] for k in reversed(list(cfg))}, indent=2))
    assert verify_replay(reordered_log, reordered_cfg).verdict == ReplayVerdict.VERIFIED_OK


# ILLEGAL: four physics/outcome failures, commitments intact
@pytest.mark.parametrize(
    "mutate", [off_board, jump_step, barrier_quota, role_wrong_capture_claim]
)
def test_physics_and_outcome_failures_illegal(mutate) -> None:
    own = mutate(honest_steps(3))
    report = verify_replay(make_log_doc(own), make_config_doc())
    ok = report.verdict == ReplayVerdict.ILLEGAL
    assert ok and all(i.code != "commitment_mismatch" for i in report.issues)


# Foreign degradation: integrity-only, physics/outcome honestly skipped
def test_foreign_degradation_verified_ok() -> None:
    own = [
        seal({"step": s, "sender": "thief", "position": [s, s], "move": "MOVE:N"})
        for s in range(3)
    ]
    report = verify_replay(make_log_doc(own), make_config_doc())
    assert report.verdict == ReplayVerdict.VERIFIED_OK
    coverage = report.coverage
    assert (coverage.integrity, coverage.physics, coverage.outcome) == (True, False, False)


# external_authenticity is never true from local recomputation alone
def test_unanchored_authenticity_always_false() -> None:
    report = verify_replay(make_log_doc(honest_steps(2)), make_config_doc())
    assert report.verdict == ReplayVerdict.VERIFIED_OK
    coverage = report.coverage
    assert (coverage.external_authenticity, coverage.bundle_digests, coverage.live_binding) == (
        False, False, False,
    )


# Deterministic report equality
def test_deterministic_report_equality() -> None:
    log = make_log_doc(honest_steps(3))
    cfg = make_config_doc()
    r1 = verify_replay(json.loads(json.dumps(log)), json.loads(json.dumps(cfg)))
    r2 = verify_replay(json.loads(json.dumps(log)), json.loads(json.dumps(cfg)))
    assert r1 == r2

    own = honest_steps(2)
    own[1]["move"] = "MOVE:W"
    tampered_log = make_log_doc(own, game_id=GAME_ID, game_uid=GAME_UID)
    t1 = verify_replay(tampered_log, cfg)
    t2 = verify_replay(tampered_log, cfg)
    assert t1 == t2
    assert t1.verdict == ReplayVerdict.TAMPERED


# live_binding: honest, per-half withheld-reveal detection (mirrors audit.py, T034/T046 feed)
def test_withheld_reveal_tampered() -> None:
    log = make_log_doc(honest_steps(2), own_committed_steps=[0, 1, 2, 3])
    report = verify_replay(log, make_config_doc())
    assert report.verdict == ReplayVerdict.TAMPERED
    withheld = [i for i in report.issues if i.code == "withheld_reveal"]
    assert withheld and withheld[0].step == 3


def test_live_binding_true_when_fully_supplied() -> None:
    log = make_log_doc(honest_steps(2), own_committed_steps=[0, 1, 2])
    report = verify_replay(log, make_config_doc())
    assert (report.verdict, report.coverage.live_binding) == (ReplayVerdict.VERIFIED_OK, True)


def test_live_binding_false_when_only_one_half_supplied() -> None:
    own = honest_steps(2, start=(3, 3))
    opp = honest_steps(1, sender="police", intent="chase", start=(0, 0))
    log = make_log_doc(own, opp, own_committed_steps=[0, 1, 2])
    report = verify_replay(log, make_config_doc())
    assert (report.verdict, report.coverage.live_binding) == (ReplayVerdict.VERIFIED_OK, False)


def test_withheld_reveal_precedence_over_physics() -> None:
    own = off_board(honest_steps(3))
    log = make_log_doc(own, own_committed_steps=[0, 1, 2, 3, 4])
    assert verdict_of(log) == ReplayVerdict.TAMPERED


# A *middle* step withheld (not trailing) breaks decode_half's contiguity check first; the
# committed ledger must still reclassify it as TAMPERED, not INVALID (ADR-008).
def test_middle_withheld_reveal_tampered() -> None:
    report = verify_replay(middle_gap_log_doc(), make_config_doc())
    assert report.verdict == ReplayVerdict.TAMPERED
    withheld = [i for i in report.issues if i.code == "withheld_reveal"]
    assert withheld and withheld[0].step == 4 and withheld[0].half == "own"


def test_middle_gap_without_ledger_stays_invalid() -> None:
    report = verify_replay(middle_gap_log_doc(committed=False), make_config_doc())
    assert report.verdict == ReplayVerdict.INVALID
    assert any(i.code == "skipped_step" for i in report.issues)


def test_middle_withheld_reveal_beats_physics_violation() -> None:
    assert verdict_of(middle_gap_log_doc(mutate=off_board)) == ReplayVerdict.TAMPERED
