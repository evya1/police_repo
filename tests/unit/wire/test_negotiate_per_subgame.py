"""Tests for per-sub-game negotiation (T052, SPEC 7.2/7.3, ADR-011).

Unit-level tests drive ``negotiated_subgame_driver`` directly over a loopback channel.
Live-lifecycle tests drive a full series exclusively through ``create_peer``/``run()``.
"""

from __future__ import annotations

import json
import threading
import time
from types import SimpleNamespace

import pytest

from common.domain.scoring import Role, role_for
from common.transport.integrity import new_nonce
from common.transport.loopback import pair
from common.transport.negotiate import our_greeting
from common.transport.refusals import Refused
from common.transport.series import PeerConfig
from police_peer.sdk import create_peer
from police_peer.wire.negotiate_per_subgame import negotiated_subgame_driver
from tests.unit.wire.test_composition_root import _SAMPLE_CONFIG

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14, "setting": "Haifa",
    "hint_max_words": 15, "axis_origin_corner": "top-left", "axis_start_index": 0,
    "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 6,
}
_BUDGETS = SimpleNamespace(turn_timeout=5.0, connect_timeout=2.0, poll_interval=0.005)


def _config(role: Role) -> PeerConfig:
    return PeerConfig(natural_role=role, budgets=_BUDGETS, terms=_TERMS, locks={})


def _stub_inner(calls: list[int]):
    def _driver(channel, engine, config, sub_game, *, evidence_sink=None):
        calls.append(sub_game)
        return object()  # a SeriesRow stand-in; these unit tests never inspect it

    return _driver


def _negotiate(driver, ch_a, ch_b, sub_game, opp_role, opp_group="B", opp_sub_game=None):
    # Drives one negotiation, scripting B's response; returns the greeting A sent.
    sent: dict = {}

    def respond():
        deadline = time.monotonic() + 5.0
        greeting = ch_b.poll_agreement()
        while greeting is None and time.monotonic() < deadline:
            time.sleep(0.005)
            greeting = ch_b.poll_agreement()
        sent.update(greeting or {})
        ch_b.send_agreement(our_greeting(
            terms=_TERMS, nonce=new_nonce(), group_id=opp_group, role=opp_role,
            sub_game_number=opp_sub_game if opp_sub_game is not None else sub_game,
        ))

    thread = threading.Thread(target=respond)
    thread.start()
    try:
        driver(ch_a, None, _config(Role.POLICE), sub_game)
    finally:
        thread.join(timeout=5)
    return sent


def _run_pair(group_a: str, group_b: str, channel_pair=None):
    # Runs a full six-sub-game series exclusively through the public composition root.
    ch_a, ch_b = channel_pair if channel_pair is not None else pair(group_a, group_b)
    peer_a = create_peer(_SAMPLE_CONFIG, channel=ch_a, role=Role.POLICE, group_id=group_a)
    peer_b = create_peer(_SAMPLE_CONFIG, channel=ch_b, role=Role.THIEF, group_id=group_b)
    results: dict[str, object] = {}
    errors: list[Exception] = []

    def go(key, peer):
        try:
            results[key] = peer.run()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=go, args=kp) for kp in (("a", peer_a), ("b", peer_b))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results.get("a"), results.get("b"), errors


# --- sub-game 1 is skipped; sub-games 2+ get a real handshake --------------------------


def test_subgame_one_skips_its_own_handshake() -> None:
    ch_a, ch_b = pair("A", "B")
    calls: list[int] = []
    negotiated_subgame_driver("A", inner=_stub_inner(calls))(ch_a, None, _config(Role.POLICE), 1)
    assert calls == [1]
    assert ch_b.poll_agreement() is None  # nothing was sent to the opponent


def test_subgame_two_negotiates_correct_alternating_role_and_calls_inner() -> None:
    # Natural role POLICE, sub-game 2 (even) alternates us to THIEF -- role_for confirms it.
    ch_a, ch_b = pair("A", "B")
    calls: list[int] = []
    driver = negotiated_subgame_driver("A", inner=_stub_inner(calls))
    sent = _negotiate(driver, ch_a, ch_b, 2, opp_role=Role.POLICE.value)
    assert calls == [2] and role_for(Role.POLICE, 2) == Role.THIEF
    assert sent["role"] == Role.THIEF.value and sent["sub_game_number"] == 2


@pytest.mark.parametrize(("opp_role", "opp_sub_game", "code"), [
    (Role.POLICE.value, 99, "SPAR-N06"),  # sub-game mismatch
    (Role.THIEF.value, None, "SPAR-N07"),  # role collision -- same as our own subgame-2 role
])
def test_pairing_mismatches_refuse(opp_role, opp_sub_game, code) -> None:
    ch_a, ch_b = pair("A", "B")
    driver = negotiated_subgame_driver("A", inner=_stub_inner([]))
    with pytest.raises(Refused) as exc:
        _negotiate(driver, ch_a, ch_b, 2, opp_role=opp_role, opp_sub_game=opp_sub_game)
    assert exc.value.code == code


# --- game_uid PROPOSED declaration: omission silent, match legal, mismatch refuses -----


def test_game_uid_omitted_on_first_negotiated_subgame_is_legal() -> None:
    ch_a, ch_b = pair("A", "B")
    driver = negotiated_subgame_driver("A", inner=_stub_inner([]))
    sent = _negotiate(driver, ch_a, ch_b, 2, opp_role=Role.POLICE.value)  # must not raise
    assert "game_uid" not in sent  # opponent unknown to us yet -- silence, not refusal


def test_game_uid_declared_and_matching_once_opponent_pinned_and_mismatch_refuses() -> None:
    ch_a, ch_b = pair("A", "B")
    driver = negotiated_subgame_driver("A", inner=_stub_inner([]))
    _negotiate(driver, ch_a, ch_b, 2, opp_role=Role.POLICE.value)  # pins opponent "B"
    sent = _negotiate(driver, ch_a, ch_b, 3, opp_role=Role.THIEF.value)
    assert "game_uid" in sent  # declared now that the opponent is pinned, and must not raise

    with pytest.raises(Refused) as exc:  # a different opponent now: refused, not re-pinned
        _negotiate(driver, ch_a, ch_b, 4, opp_role=Role.POLICE.value, opp_group="stranger")
    assert exc.value.code == "SPAR-N10"


# --- live lifecycle: full six-sub-game series through the public composition root ------


def test_full_series_declares_1_through_6_stable_ids_and_alternating_roles() -> None:
    result_a, result_b, errors = _run_pair("teamA", "teamB")
    assert not errors and result_a is not None and result_b is not None
    assert [row.sub_game_number for row in result_a.ledger] == list(range(1, 7))
    assert result_a.game_id == result_b.game_id != ""
    assert result_a.game_uid == result_b.game_uid
    assert all(row.role == role_for(Role.POLICE, row.sub_game_number) for row in result_a.ledger)
    for row_a, row_b in zip(result_a.ledger, result_b.ledger, strict=True):
        assert row_a.role != row_b.role  # complementary every sub-game
    assert all(row.audit_ok for row in result_a.ledger)


def test_thief_takes_the_first_turn_every_subgame() -> None:
    # Whichever peer plays POLICE must have observed THIEF's own step 1 on the wire.
    result_a, _result_b, errors = _run_pair("teamA2", "teamB2")
    assert not errors
    for evidence in result_a.replay_evidence:
        if evidence.row.role == Role.POLICE:
            first = next(
                json.loads(r.payload_bytes) for r in evidence.opponent_records if r.step == 1
            )
            assert first["sender"] == Role.THIEF.value


def test_no_cross_subgame_state_leak_after_a_tampered_subgame() -> None:
    # A commitment fault forced into sub-game 2 must sanction only sub-game 2; sub-game 3
    # (fresh runtime state) must settle cleanly right after it.
    ch_a, ch_b = pair("teamA3", "teamB3")
    original_send_audit = ch_a.send_audit
    call_count = {"n": 0}

    def tampering_send_audit(payload: dict):
        call_count["n"] += 1
        if call_count["n"] == 2 and len(payload.get("records", [])) > 1:  # sub-game 2's audit
            payload = dict(payload)
            records = list(payload["records"])
            # Corrupt the COMMITTED bytes. On the default (`reference-v3`) lane those live
            # nested under `payload`; a top-level `move` would only add a stray sibling of
            # `payload` that the verifier rightly ignores, leaving the record re-hashing
            # clean and this test passing for the wrong reason. If the default ever moves
            # back to a flat lane this raises KeyError -- loudly, which is the point.
            records[-1] = dict(records[-1], payload=dict(records[-1]["payload"], move="X"))
            payload["records"] = records
        return original_send_audit(payload)

    ch_a.send_audit = tampering_send_audit  # type: ignore[method-assign]

    result_a, result_b, errors = _run_pair("teamA3", "teamB3", channel_pair=(ch_a, ch_b))
    assert not errors and result_a is not None and result_b is not None

    subgame_two_b = next(row for row in result_b.ledger if row.sub_game_number == 2)
    subgame_three_a = next(row for row in result_a.ledger if row.sub_game_number == 3)
    subgame_three_b = next(row for row in result_b.ledger if row.sub_game_number == 3)
    assert subgame_two_b.audit_ok is False  # B detected A's tampered sub-game-2 audit
    assert subgame_three_a.audit_ok is True  # unaffected -- fresh state, no leak
    assert subgame_three_b.audit_ok is True
    assert result_a.game_id == result_b.game_id  # identity survives the fault too
    assert result_a.game_uid == result_b.game_uid
