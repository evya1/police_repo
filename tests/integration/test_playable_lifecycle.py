from __future__ import annotations

import threading

import pytest

from common.domain.scoring import Outcome, Role, role_for
from common.transport.loopback import pair
from common.transport.series import PeerConfig, run_series
from common.transport.subgame import play_subgame
from police_peer.wire import BrainDrivenEngine


class DummyBudgets:
    turn_timeout = 5.0
    connect_timeout = 5.0
    poll_interval = 0.005


_full_terms = {
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


def test_playable_lifecycle_real() -> None:
    ch_a, ch_b = pair()

    cfg_a = PeerConfig(Role.POLICE, DummyBudgets(), _full_terms, seed=1)
    cfg_b = PeerConfig(Role.THIEF, DummyBudgets(), _full_terms, seed=2)

    eng_a = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, config={})
    eng_b = BrainDrivenEngine(Role.THIEF, board_size=7, seed=2, config={})

    res_a, res_b = run_series(ch_a, ch_b, cfg_a, cfg_b, eng_a, eng_b)

    assert res_a.settled is True
    assert res_b.settled is True
    assert len(res_a.ledger) == 6
    assert len(res_b.ledger) == 6

    for i in range(6):
        row_a = res_a.ledger[i]
        row_b = res_b.ledger[i]
        assert row_a.sub_game_number == i + 1
        assert row_b.sub_game_number == i + 1
        assert row_a.role is role_for(Role.POLICE, i + 1)
        assert row_b.role is role_for(Role.THIEF, i + 1)
        assert row_a.outcome == row_b.outcome
        assert row_a.steps == row_b.steps
        assert row_a.score_police == row_b.score_police
        assert row_a.score_thief == row_b.score_thief
        assert row_a.audit_ok is True
        assert row_b.audit_ok is True
        assert row_a.steps > 0


class EarlyCapturePoliceEngine(BrainDrivenEngine):
    """Engine that issues a capture claim on step 2 at thief position."""

    def decide(self) -> dict:
        res = super().decide()
        engine = self._session.engine if self._session is not None else None
        if engine and engine.role is Role.POLICE and engine.step == 2:
            res["capture_claim"] = [3, 3]
        return res


class FixedThiefEngine(BrainDrivenEngine):
    """Thief that stays at (3, 3)."""

    def decide(self) -> dict:
        if self._session is None or self._session.engine is None:
            raise RuntimeError("engine not started")
        move = "STAY"
        self._session.apply_move(move)
        engine = self._session.engine
        trail = self._session.trail
        res = {
            "move": move,
            "hint": "I am staying",
            "state": engine.state_string(),
            "smell_grid": trail.full_turn(engine.position) if trail is not None else {},
        }
        if self._session.pending_claim is not None:
            ans = engine.answer_capture_claim(
                self._session.pending_claim, at=self._session.pending_claim_position
            )
            res["claim_response"] = ans
            self._session.pending_claim = None
            self._session.pending_claim_position = None
            if ans and ans.get("caught") is True:
                self._session.thief_caught = True
                res["win_claim"] = {"type": "capture"}
                return res
        if engine.self_captured():
            res["win_claim"] = {"type": "capture"}
        elif engine.survived():
            res["win_claim"] = {"type": "survival"}
        return res


def test_early_capture_deterministic() -> None:
    """Exercise a legitimate early-capture path at step 3."""
    ch_a, ch_b = pair("Police", "Thief")
    cfg_a = PeerConfig(Role.POLICE, DummyBudgets(), _full_terms, seed=1)
    cfg_b = PeerConfig(Role.THIEF, DummyBudgets(), _full_terms, seed=2)

    eng_a = EarlyCapturePoliceEngine(Role.POLICE, board_size=7, seed=1, config={})
    eng_b = FixedThiefEngine(Role.THIEF, board_size=7, seed=2, config={})

    row_a = row_b = None
    errors: list[Exception] = []

    def run_a():
        nonlocal row_a
        try:
            row_a = play_subgame(ch_a, eng_a, cfg_a, 1)
        except Exception as e:
            errors.append(e)

    def run_b():
        nonlocal row_b
        try:
            row_b = play_subgame(ch_b, eng_b, cfg_b, 1)
        except Exception as e:
            errors.append(e)

    t_a = threading.Thread(target=run_a)
    t_b = threading.Thread(target=run_b)
    t_a.start()
    t_b.start()
    t_a.join(timeout=10)
    t_b.join(timeout=10)

    if errors:
        raise RuntimeError(f"Errors in play_subgame: {errors}")

    assert row_a is not None and row_b is not None
    assert row_a.outcome == Outcome.CAPTURE
    assert row_b.outcome == Outcome.CAPTURE
    assert row_a.steps == 3
    assert row_b.steps == 3
    assert row_a.score_police == 20
    assert row_a.score_thief == 5
    assert row_a.audit_ok is True
    assert row_b.audit_ok is True


def test_survival_threshold_boundaries() -> None:
    """Exercise 34/35/36 survival boundaries and divergence refusal."""
    eng = BrainDrivenEngine(Role.THIEF, board_size=7, config={})

    # 35 threshold
    eng.start_subgame(1, Role.THIEF, terms={"max_steps": 35, "survival_threshold": 35})
    assert eng._session.engine.step == 0
    eng._session.engine.step = 34
    assert eng._session.engine.survived() is False
    eng._session.engine.step = 35
    assert eng._session.engine.survived() is True

    # 36 threshold
    eng.start_subgame(1, Role.THIEF, terms={"max_steps": 36, "survival_threshold": 36})
    eng._session.engine.step = 35
    assert eng._session.engine.survived() is False
    eng._session.engine.step = 36
    assert eng._session.engine.survived() is True

    # Divergent configuration must refuse
    with pytest.raises(ValueError, match="termination contract"):
        eng.start_subgame(1, Role.THIEF, terms={"max_steps": 34, "survival_threshold": 35})
