"""Unit tests for subgame driver, state machine transitions, and timeout behavior."""

from __future__ import annotations

import pytest

from common.domain.scoring import Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig
from common.transport.subgame import play_subgame
from police_peer.wire import StandInEngine


class DummyBudgets:
    """Minimal budgets for testing."""

    turn_timeout = 30.0
    connect_timeout = 30.0
    poll_interval = 0.01


class _TightBudgets:
    """Tight budgets for deadline test."""

    turn_timeout = 0.05
    connect_timeout = 30.0
    poll_interval = 0.01


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


def test_driver_raises_on_deadline_timeout() -> None:
    """Driver raises TimeoutError when the opponent never sends a turn."""
    class DropTurnChannel:
        def __init__(self, inner):
            self._inner = inner

        def send_turn(self, message):
            pass

        def poll_turn(self):
            return None

        def send_agreement(self, message):
            self._inner.send_agreement(message)

        def poll_agreement(self):
            return self._inner.poll_agreement()

        def send_audit(self, message):
            self._inner.send_audit(message)

        def poll_audit(self):
            return None

        def flush(self):
            pass

    ch_a, _ch_b = pair("Police", "Thief")
    ch_a_dropped = DropTurnChannel(ch_a)
    config = PeerConfig(natural_role=Role.POLICE, budgets=_TightBudgets(), terms=_full_terms, seed=42)
    engine = StandInEngine(Role.POLICE)

    with pytest.raises(TimeoutError):
        play_subgame(ch_a_dropped, engine, config, 1)
