"""Failing-first test: every outgoing turn carries the required public keys.

Item 6 of the repair task's required tests. Sealed-only fields (state,
verdict, reasoning, prompt_text, nonce) must never leak into the public
projection.
"""

from __future__ import annotations

from common.domain.scoring import Role
from common.transport.subgame import _our_move
from police_peer.wire.brain import BrainDrivenEngine

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}


def test_every_outgoing_turn_carries_required_keys() -> None:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=3, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    message, _record = _our_move(engine, Role.POLICE, is_thief=False, lap=1, sub_game=1)
    for key in ("step", "sender", "hint", "smell_grid", "commit", "timestamp"):
        assert key in message, f"missing required public key: {key}"
    assert message["timestamp"]


def test_sealed_only_fields_never_leak_into_the_public_turn() -> None:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=3, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    message, record = _our_move(engine, Role.POLICE, is_thief=False, lap=1, sub_game=1)
def test_sealed_only_fields_never_leak_into_the_public_turn() -> None:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=3, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    message, record = _our_move(engine, Role.POLICE, is_thief=False, lap=1, sub_game=1)
    # reference-v3 audits the SIGNED payload (record.payload), not the record envelope.
    # ``nonce`` is a record-envelope field (it is never part of the signed payload); the
    # rest are signed payload fields. None of them may leak into the public turn message.
    signed = record["payload"]
    for sealed_only in ("state", "verdict", "reasoning", "prompt_text"):
        assert sealed_only not in message, f"sealed field {sealed_only} leaked into public turn"
        assert sealed_only in signed, f"sealed field {sealed_only} missing from the audit record"
    assert "nonce" not in message, "sealed field nonce leaked into public turn"
    assert "nonce" in record, "sealed field nonce missing from the audit record"
