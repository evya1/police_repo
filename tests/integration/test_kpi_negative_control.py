"""Failing-first test: an outcome-based negative control fails the capture KPI.

Item 10 of the repair task's required tests: an engine that never pursues
and never claims a capture must fail the >=60% capture-rate bar, proving the
KPI measures something real rather than an artifact of the harness.
"""

from __future__ import annotations

import random
import threading

from common.domain.scoring import Outcome, Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig
from common.transport.subgame import play_subgame
from police_peer.wire.session import SubgameSession

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}


class _Budgets:
    turn_timeout = 5.0
    connect_timeout = 5.0
    poll_interval = 0.005


class _NeverPursuesEngine:
    """Always STAYs, never places a barrier, never claims a capture."""

    def __init__(self) -> None:
        self._session: SubgameSession | None = None

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        self._session = SubgameSession(natural_role=Role.POLICE, board_size=7, seed=1)
        self._session.start(sub_game, role, terms=terms or {})

    def decide(self) -> dict:
        self._session.apply_move("STAY")
        res = self._session.build_result(move="STAY", hint="idle")
        res.pop("capture_claim", None)  # the negative control: never claims
        return res

    def observe_opponent(self, message: dict) -> None:
        if self._session is not None:
            self._session.observe_barrier_and_claims(message)

    def terminal(self) -> Outcome | None:
        return self._session.terminal() if self._session else None

    def terminal_final(self) -> dict | None:
        if self._session is None or self.terminal() is None:
            return None
        self._session.apply_move("STAY")
        trail = self._session.trail
        smell = trail.full_turn(self._session.engine.position) if trail else {}
        return {
            "move": "STAY", "hint": "", "state": self._session.engine.state_string(),
            "smell_grid": smell,
        }


class _RandomThief:
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self._session: SubgameSession | None = None

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        self._session = SubgameSession(natural_role=Role.THIEF, board_size=7, seed=1)
        self._session.start(sub_game, role, terms=terms or {})

    def decide(self) -> dict:
        legal = self._session.engine.legal_moves()
        move = self._rng.choice(legal)
        self._session.apply_move(move)
        return self._session.build_result(move=move, hint="")

    def observe_opponent(self, message: dict) -> None:
        if self._session is not None:
            self._session.observe_barrier_and_claims(message)

    def terminal(self) -> Outcome | None:
        return self._session.terminal() if self._session else None

    def terminal_final(self) -> dict | None:
        return None


def _play_one(seed: int) -> Outcome:
    a, b = pair("Police", "Thief")
    cfg_a = PeerConfig(Role.POLICE, _Budgets(), _TERMS, seed=seed)
    cfg_b = PeerConfig(Role.THIEF, _Budgets(), _TERMS, seed=seed + 500)
    police_engine = _NeverPursuesEngine()
    thief_engine = _RandomThief(seed + 500)
    result: dict[str, object] = {}
    errors: list[Exception] = []

    def run_a() -> None:
        try:
            result["row"] = play_subgame(a, police_engine, cfg_a, 1)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def run_b() -> None:
        try:
            play_subgame(b, thief_engine, cfg_b, 1)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    ta, tb = threading.Thread(target=run_a), threading.Thread(target=run_b)
    ta.start()
    tb.start()
    ta.join(timeout=30)
    tb.join(timeout=30)
    if errors:
        raise RuntimeError(f"negative-control errors: {errors}")
    return result["row"].outcome


def test_never_pursues_never_claims_engine_fails_capture_kpi() -> None:
    games = 6
    captures = sum(1 for i in range(games) if _play_one(i) is Outcome.CAPTURE)
    capture_rate = captures / games
    assert capture_rate < 0.60, (
        f"negative control (never pursues, never claims) unexpectedly cleared the "
        f"60% KPI bar: {capture_rate:.2%}"
    )
