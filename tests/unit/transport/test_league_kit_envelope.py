"""Tests for the kit audit-envelope anti-corruption adapter (T052, ADR-011)."""

from __future__ import annotations

import json

import pytest

from common.transport.canonical import canonical_bytes
from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce
from common.transport.league_kit_envelope import (
    KitCorroborationFinding,
    classify_capture,
    corroborate_answer,
    corroborate_concession,
    evaluate_capture_corroboration,
    parse_kit_position,
    steps_agree,
    terminal_step_delta_ok,
    unwrap_inbound,
    unwrap_inbound_records,
    verify_kit_bundle,
    wrap_outbound,
    wrap_outbound_records,
)
from common.transport.replay import verify_replay
from common.transport.replay_types import ReplayVerdict
from tests.unit.transport.replay_fixtures import (
    honest_steps,
    make_config_doc,
    make_log_doc,
    nested,
    seal,
)


def _round_trip(records):
    return unwrap_inbound_records(wrap_outbound_records(records))


def _verify(records):
    return verify_replay(make_log_doc(records), make_config_doc())


# --- envelope wrap/unwrap: one commitment authority, never re-hashed -------------------


def test_wrap_outbound_never_rehashes_and_preserves_payload() -> None:
    payload = {"step": 1, "sender": "thief", "state": "grid=7x7;self=[3, 4];barriers=[]"}
    record = seal(payload)
    wrapped = wrap_outbound(record)
    assert wrapped == {"payload": payload, "nonce": record["nonce"], "commit": record["commit"]}
    assert hash_commit(wrapped["payload"], wrapped["nonce"]) == record["commit"]  # not re-hashed
    many = wrap_outbound_records(honest_steps(2))
    assert all("payload" in w and "commit" in w and "nonce" in w for w in many)


def test_unwrap_inbound_normalizes_nested_to_flat() -> None:
    payload = {"step": 2, "sender": "police", "state": "grid=7x7;self=[0, 1];barriers=[]"}
    nonce = new_nonce()
    kit_record = {"payload": payload, "nonce": nonce, "commit": hash_commit(payload, nonce)}
    assert unwrap_inbound(kit_record) == {**payload, "nonce": nonce, "commit": kit_record["commit"]}


def test_unwrap_inbound_leaves_already_flat_record_alone() -> None:
    record = seal({"step": 0, "sender": "thief", "intent": "declare"})
    assert unwrap_inbound(record) == record  # no "payload" key -> already flat


def test_unwrap_inbound_records_non_list_passes_through() -> None:
    assert unwrap_inbound_records(None) is None and unwrap_inbound_records("nope") == "nope"


def test_round_trip_through_verifier_no_verdict_change() -> None:
    own = honest_steps(3)
    baseline, adapted = _verify(own), _verify(_round_trip(own))
    assert adapted.verdict == baseline.verdict == ReplayVerdict.VERIFIED_OK
    assert adapted.checked_records == baseline.checked_records
    # T033's own strict decoder already tells nested from flat per record (unchanged)
    assert _verify([nested({"step": 0, "sender": "thief", "intent": "declare"})]).verdict == (
        ReplayVerdict.VERIFIED_OK
    )


def test_hebrew_emoji_ensure_ascii_false() -> None:
    payload = {"step": 1, "sender": "thief", "hint": "שלום 🎲"}
    wrapped = wrap_outbound(seal(payload))
    raw = json.dumps(wrapped["payload"], sort_keys=True, ensure_ascii=False)
    assert "שלום" in raw and "🎲" in raw and "\\u" not in raw
    assert canonical_bytes(payload) == json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


# --- terminal-final corrections (SPEC 3.1) ---------------------------------------------


@pytest.mark.parametrize(("a", "b", "ok"), [(10, 10, True), (10, 11, True), (11, 10, True),
                                             (10, 12, False), (5, 8, False)])
def test_steps_agree_within_one(a, b, ok) -> None:
    assert steps_agree(a, b) is ok


@pytest.mark.parametrize(("prev", "curr", "ok"), [
    ((3, 3), (3, 3), True), ((3, 3), (3, 4), True),
    ((3, 3), (3, 5), False), ((3, 3), (5, 5), False),
    (None, (3, 3), True), ((3, 3), None, True),
])
def test_terminal_step_delta_ok(prev, curr, ok) -> None:
    assert terminal_step_delta_ok(prev, curr) is ok


def test_parse_kit_position_strict() -> None:
    assert parse_kit_position({"position": [2, 5]}) == (2, 5)


@pytest.mark.parametrize("payload", [{}, {"position": "2,5"}, {"position": [2]},
                                      {"position": [True, 5]}, "not-a-dict"])
def test_parse_kit_position_degrades_never_guesses(payload) -> None:
    assert parse_kit_position(payload) is None


# --- answer vs. concession classification & corroboration ------------------------------


def test_classify_capture() -> None:
    assert classify_capture((3, 3), {"claim": [3, 3], "caught": True}) == "answer"
    assert classify_capture((3, 3), {"claim": [4, 3], "caught": True}) == "concession"
    assert classify_capture((3, 3), None) is None
    assert classify_capture((3, 3), {"claim": [4, 3], "caught": False}) is None


def test_corroborate_answer() -> None:
    assert corroborate_answer((3, 3), (3, 3)) == KitCorroborationFinding("answer", True, "")
    bad = corroborate_answer((3, 3), (2, 3))
    assert bad.kind == "answer" and not bad.corroborated and bad.reason


def test_corroborate_concession_rules_46_and_47_use_cops_own_barriers() -> None:
    assert corroborate_concession((4, 4), {(4, 4)}, board_size=7).corroborated  # rule 46
    neighbours = {(3, 4), (5, 4), (4, 3), (4, 5)}
    assert corroborate_concession((4, 4), neighbours, board_size=7).corroborated  # rule 47
    assert not corroborate_concession((4, 4), set(), board_size=7).corroborated  # no cop barrier


def test_evaluate_capture_corroboration_routes_by_kind() -> None:
    answer = evaluate_capture_corroboration(
        cop_claim=(3, 3), claim_response={"claim": [3, 3], "caught": True},
        thief_trail_end=(3, 3), cop_own_barriers=set(), board_size=7,
    )
    assert answer.kind == "answer" and answer.corroborated
    concession = evaluate_capture_corroboration(
        cop_claim=(3, 3), claim_response={"claim": [4, 4], "caught": True},
        thief_trail_end=(9, 9), cop_own_barriers={(4, 4)}, board_size=7,
    )
    assert concession.kind == "concession" and concession.corroborated
    assert evaluate_capture_corroboration(
        cop_claim=(3, 3), claim_response=None, thief_trail_end=None,
        cop_own_barriers=set(), board_size=7,
    ) is None


# --- verify_kit_bundle: layered finding, taxonomy preserved -----------------------------


def test_verify_kit_bundle_downgrades_verified_ok_to_illegal_on_failed_corroboration() -> None:
    log, cfg = make_log_doc(honest_steps(2)), make_config_doc()
    assert _verify(honest_steps(2)).verdict == ReplayVerdict.VERIFIED_OK
    bad = KitCorroborationFinding("concession", False, "cop's own barriers do not support it")
    report = verify_kit_bundle(log, cfg, finding=bad)
    assert report.verdict == ReplayVerdict.ILLEGAL
    assert any(i.code == "capture_corroboration_failed" for i in report.issues)


def test_verify_kit_bundle_never_relabels_tampered() -> None:
    own = honest_steps(2)
    own[1]["move"] = "MOVE:W"  # stale commit -- commitment_mismatch, TAMPERED
    log, cfg = make_log_doc(own), make_config_doc()
    assert _verify(own).verdict == ReplayVerdict.TAMPERED
    bad = KitCorroborationFinding("answer", False, "trail mismatch")
    report = verify_kit_bundle(log, cfg, finding=bad)
    assert report.verdict == ReplayVerdict.TAMPERED  # never downgraded/relabeled
    assert any(i.code == "capture_corroboration_failed" for i in report.issues)


def test_verify_kit_bundle_passthrough_when_corroborated() -> None:
    log, cfg = make_log_doc(honest_steps(2)), make_config_doc()
    good = KitCorroborationFinding("answer", True, "")
    assert verify_kit_bundle(log, cfg, finding=good) == verify_replay(log, cfg)


def test_unparseable_position_degrades_coverage_not_tampering() -> None:
    own = [seal({"step": s, "sender": "thief", "position": [s, s]}) for s in range(3)]
    report = _verify(_round_trip(own))
    assert report.verdict == ReplayVerdict.VERIFIED_OK
    assert (report.coverage.physics, report.coverage.outcome) == (False, False)


# --- regression: existing T033 TAMPERED-vs-INVALID distinction, unchanged through envelope ---


def test_regression_stale_digest_vs_malformed_commitment_through_envelope() -> None:
    stale = honest_steps(3)
    stale[2]["move"] = "MOVE:W"  # payload mutated, commit left stale -> TAMPERED
    tampered_report = _verify(_round_trip(stale))
    assert tampered_report.verdict == ReplayVerdict.TAMPERED
    assert any(i.step == 2 for i in tampered_report.issues)

    malformed = honest_steps(1)
    malformed[1]["commit"] = "not-64-hex"  # structurally bad -> INVALID, not TAMPERED
    assert _verify(_round_trip(malformed)).verdict == ReplayVerdict.INVALID
