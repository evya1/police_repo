"""Production-path sealed `position` evidence (T054).

The pinned kit's `examples/verify_pairing_physics.py` dereferences `payload["position"]`
for every step it walks. The kit's *basic* audit tolerates its absence by skipping physics
entirely -- interoperability-safe, but not evidence -- so omission cannot satisfy a full
14-artifact verification. These pin the field at the one boundary that seals it.
"""

from __future__ import annotations

from common.transport.turnseal import PUBLIC_TURN_KEYS
from tests.integration.kit_audit_harness import run_pair, sealed_payloads


def test_production_sealed_record_binds_post_move_position() -> None:
    result, _ = run_pair()
    moves = [p for p in sealed_payloads(result) if p.get("step") != 0]
    assert moves, "series produced no sealed move records"
    missing = [p["step"] for p in moves if "position" not in p]
    assert not missing, f"sealed records omit post-move position at steps {missing}"


def test_sealed_position_agrees_with_sealed_state() -> None:
    """The walker cross-checks `position` against `state`'s own `self=[r, c]` spelling; a
    disagreement is reported as a physics failure, so they must be one derivation."""
    result, _ = run_pair()
    checked = 0
    for payload in sealed_payloads(result):
        if payload.get("step") == 0 or "position" not in payload:
            continue
        row, col = payload["position"]
        assert payload["state"].split("self=")[-1].split(";")[0] == f"[{row}, {col}]"
        checked += 1
    assert checked, "no sealed move records carried a position to cross-check"


def test_position_never_leaks_into_the_public_turn_projection() -> None:
    """Sealed/audit-only. A public turn carrying our own cell would hand the opponent the
    objective state the whole hidden-state game exists to withhold."""
    assert "position" not in PUBLIC_TURN_KEYS
