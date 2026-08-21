"""Contract: live PeerFacade exchange with scent model lock verification."""

from __future__ import annotations

import threading

from common.domain.scoring import Outcome, Role
from common.transport.loopback import pair
from common.transport.refusals import Refused
from common.transport.series import PeerConfig, PeerFacade
from police_peer.scent.lock import model_lock_hash


class DummyBudgets:
    turn_timeout: float = 2.0
    connect_timeout: float = 2.0
    poll_interval: float = 0.005


class DummyEngine:
    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        pass

    def decide(self) -> dict:
        return {"move": "STAY", "hint": "here"}

    def observe_opponent(self, message: dict) -> None:
        pass

    def terminal(self) -> Outcome | None:
        return None


def _terms() -> dict:
    return {
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


def test_live_peer_facade_exchange_greeting_with_matching_locks() -> None:
    chan_a, chan_b = pair()
    terms = _terms()
    scent_hash = model_lock_hash("subtractive_chebyshev_v1")
    config_a = PeerConfig(
        natural_role=Role.POLICE,
        budgets=DummyBudgets(),
        terms=terms,
        locks={"scent_model": scent_hash},
    )
    config_b = PeerConfig(
        natural_role=Role.THIEF,
        budgets=DummyBudgets(),
        terms=terms,
        locks={"scent_model": scent_hash},
    )
    facade_a = PeerFacade(chan_a, DummyEngine(), config_a, name="team-a")
    facade_b = PeerFacade(chan_b, DummyEngine(), config_b, name="team-b")

    t_a = threading.Thread(target=facade_a._exchange_greeting)
    t_b = threading.Thread(target=facade_b._exchange_greeting)
    t_a.start()
    t_b.start()
    t_a.join(timeout=5)
    t_b.join(timeout=5)

    assert facade_a._game_id != ""
    assert facade_b._game_id != ""


def test_live_peer_facade_exchange_greeting_with_mismatched_locks_refuses() -> None:
    chan_a, chan_b = pair()
    terms = _terms()
    hash_a = model_lock_hash("subtractive_chebyshev_v1")
    hash_b = model_lock_hash("multiplicative_book_v1")
    config_a = PeerConfig(
        natural_role=Role.POLICE,
        budgets=DummyBudgets(),
        terms=terms,
        locks={"scent_model": hash_a},
    )
    config_b = PeerConfig(
        natural_role=Role.THIEF,
        budgets=DummyBudgets(),
        terms=terms,
        locks={"scent_model": hash_b},
    )
    facade_a = PeerFacade(chan_a, DummyEngine(), config_a, name="team-a")
    facade_b = PeerFacade(chan_b, DummyEngine(), config_b, name="team-b")

    errors_a: list[Exception] = []
    errors_b: list[Exception] = []

    def run_a() -> None:
        try:
            facade_a._exchange_greeting()
        except Exception as e:
            errors_a.append(e)

    def run_b() -> None:
        try:
            facade_b._exchange_greeting()
        except Exception as e:
            errors_b.append(e)

    t_a = threading.Thread(target=run_a)
    t_b = threading.Thread(target=run_b)
    t_a.start()
    t_b.start()
    t_a.join(timeout=5)
    t_b.join(timeout=5)

    assert len(errors_a) == 1
    assert isinstance(errors_a[0], Refused)
    assert errors_a[0].code == "SPAR-N05"
    assert len(errors_b) == 1
    assert isinstance(errors_b[0], Refused)
    assert errors_b[0].code == "SPAR-N05"
