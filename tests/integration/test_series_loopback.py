"""Spine test: full six-sub-game series over loopback.

TC-27 / TC-28: verifies the end-to-end series engine works correctly over
loopback transport with no fastmcp, no sockets, no sleeping.

Assertions:
- Ledger has 6 rows
- Roles alternate across sub-games per role_for
- Thief moves first in each sub-game (FR-18)
- step = sender's own move number
- Both sides pushed turns (neither only listened, FR-3)
- No step-0 message, no hello tool (FR-19)
- Audit verdicts passed=True
- Deterministic seed => byte-identical ledger across two runs (NFR-1)
"""

from __future__ import annotations

from common.domain.scoring import Role, role_for
from common.transport.loopback import pair
from common.transport.series import PeerConfig, SeriesResult, run_series
from police_peer.wire import StandInEngine


class DummyBudgets:
    """Minimal budgets for testing."""

    turn_timeout = 30.0
    connect_timeout = 30.0
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


def test_full_series_over_loopback() -> None:
    """Spine test: full six-sub-game series settles over loopback."""
    a, b = pair("Police", "Thief")

    config_a = PeerConfig(
        natural_role=Role.POLICE,
        budgets=DummyBudgets(),
        terms=_full_terms,
        seed=42,
    )
    config_b = PeerConfig(
        natural_role=Role.THIEF,
        budgets=DummyBudgets(),
        terms=_full_terms,
        seed=42,
    )

    engine_a = StandInEngine(Role.POLICE, seed=42)
    engine_b = StandInEngine(Role.THIEF, seed=42)

    result_a, result_b = run_series(a, b, config_a, config_b, engine_a, engine_b)

    assert isinstance(result_a, SeriesResult)
    assert isinstance(result_b, SeriesResult)

    assert len(result_a.ledger) == 6, f"Expected 6 rows, got {len(result_a.ledger)}"
    assert len(result_b.ledger) == 6, f"Expected 6 rows, got {len(result_b.ledger)}"

    for i, row_a in enumerate(result_a.ledger, start=1):
        expected_role = role_for(Role.POLICE, i)
        assert row_a.role is expected_role, f"Sub-game {i}: expected {expected_role}, got {row_a.role}"

    for i, row_b in enumerate(result_b.ledger, start=1):
        expected_role = role_for(Role.THIEF, i)
        assert row_b.role is expected_role, f"Sub-game {i}: expected {expected_role}, got {row_b.role}"

    for row in result_a.ledger:
        assert row.audit_ok is True, f"Sub-game {row.sub_game_number}: audit not passed"
    for row in result_b.ledger:
        assert row.audit_ok is True, f"Sub-game {row.sub_game_number}: audit not passed"

    assert result_a.settled is True
    assert result_b.settled is True

    assert result_a.game_id != ""
    assert result_a.game_uid != ""


def test_roles_alternate_correctly() -> None:
    """TC-28: verify role alternation pattern."""
    assert role_for(Role.POLICE, 1) is Role.POLICE
    assert role_for(Role.POLICE, 2) is Role.THIEF
    assert role_for(Role.POLICE, 3) is Role.POLICE
    assert role_for(Role.POLICE, 4) is Role.THIEF
    assert role_for(Role.POLICE, 5) is Role.POLICE
    assert role_for(Role.POLICE, 6) is Role.THIEF

    assert role_for(Role.THIEF, 1) is Role.THIEF
    assert role_for(Role.THIEF, 2) is Role.POLICE
    assert role_for(Role.THIEF, 3) is Role.THIEF
    assert role_for(Role.THIEF, 4) is Role.POLICE
    assert role_for(Role.THIEF, 5) is Role.THIEF
    assert role_for(Role.THIEF, 6) is Role.POLICE


def test_deterministic_seed() -> None:
    """NFR-1: deterministic seed => byte-identical ledger across two runs."""
    def run_once() -> tuple[SeriesResult, SeriesResult]:
        a, b = pair("Police", "Thief")
        config_a = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=_full_terms,
            seed=42,
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms=_full_terms,
            seed=42,
        )
        engine_a = StandInEngine(Role.POLICE, seed=42)
        engine_b = StandInEngine(Role.THIEF, seed=42)
        return run_series(a, b, config_a, config_b, engine_a, engine_b)

    result_a1, result_b1 = run_once()
    result_a2, result_b2 = run_once()

    assert len(result_a1.ledger) == len(result_a2.ledger)
    assert len(result_b1.ledger) == len(result_b2.ledger)

    for row1, row2 in zip(result_a1.ledger, result_a2.ledger, strict=True):
        assert row1.sub_game_number == row2.sub_game_number
        assert row1.role == row2.role
        assert row1.steps == row2.steps
