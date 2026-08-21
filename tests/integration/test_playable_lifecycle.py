from __future__ import annotations

from common.domain.scoring import Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig, run_series
from src.police_peer.wire import StandInEngine


class DummyBudgets:
    turn_timeout = 5.0
    connect_timeout = 5.0
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

def test_playable_lifecycle_real():
    ch_a, ch_b = pair()

    cfg_a = PeerConfig(Role.POLICE, DummyBudgets(), _full_terms, seed=1)
    cfg_b = PeerConfig(Role.THIEF, DummyBudgets(), _full_terms, seed=2)

    eng_a = StandInEngine(Role.POLICE, board_size=7, seed=1)
    eng_b = StandInEngine(Role.THIEF, board_size=7, seed=2)

    res_a, res_b = run_series(ch_a, ch_b, cfg_a, cfg_b, eng_a, eng_b)

    assert res_a.settled is True
    assert res_b.settled is True

    for row in res_a.ledger:
        assert row.audit_ok is True
        assert row.steps > 0
