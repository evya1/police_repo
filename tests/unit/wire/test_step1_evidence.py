"""Failing-first test: Police applies Thief's step-1 evidence before deciding.

Item 3 of the repair task's required tests: a spy on ``apply_half_turn`` and
on the brain's ``decide`` proves the canonical belief update runs exactly
once, and strictly before the first ``decide()`` call.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Role
from common.transport.subgame import _our_move
from police_peer.wire.brain import BrainDrivenEngine
from police_peer.wire.session import SubgameSession

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}


def test_apply_half_turn_called_once_before_decide(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)

    import police_peer.belief.update as update_mod

    real_apply = update_mod.apply_half_turn

    def apply_spy(*args, **kwargs):
        calls.append("apply_half_turn")
        return real_apply(*args, **kwargs)

    monkeypatch.setattr(update_mod, "apply_half_turn", apply_spy)

    real_decide = engine._brain.decide

    def decide_spy(*args, **kwargs):
        calls.append("decide")
        return real_decide(*args, **kwargs)

    monkeypatch.setattr(engine._brain, "decide", decide_spy)

    thief_session = SubgameSession(natural_role=Role.THIEF, board_size=7, seed=9)
    thief_session.start(1, Role.THIEF, terms=_TERMS)

    class _FixedThief:
        def decide(self) -> dict:
            thief_session.apply_move("STAY")
            return thief_session.build_result(move="STAY", hint="scouting")

    message, _record = _our_move(_FixedThief(), Role.THIEF, is_thief=True, lap=1, sub_game=1)
    engine.observe_opponent(message)
    engine.decide()

    assert calls.count("apply_half_turn") == 1
    assert calls == ["apply_half_turn", "decide"]
