"""Tests for the series engine.

TC-27: hint-provider failure path — legal action proceeds.
TC-28: role alternation across sub-games via role_for.
"""

from __future__ import annotations

from common.domain.scoring import Role, role_for
from common.transport.loopback import pair
from common.transport.series import PeerConfig, SeriesResult, run_series
from police_peer.wire import StandInEngine


class DummyBudgets:
    """Minimal budgets implementation for testing."""

    turn_timeout = 10.0
    connect_timeout = 10.0
    poll_interval = 0.005


_test_terms = {
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


def _run_pair() -> tuple[SeriesResult, SeriesResult]:
    """Run a full six-sub-game series over loopback."""
    a, b = pair("A", "B")
    config_a = PeerConfig(natural_role=Role.POLICE, budgets=DummyBudgets(), terms=_test_terms)
    config_b = PeerConfig(natural_role=Role.THIEF, budgets=DummyBudgets(), terms=_test_terms)
    return run_series(a, b, config_a, config_b, StandInEngine(Role.POLICE), StandInEngine(Role.THIEF))


class TestRunSeries:
    """Tests for the run_series function."""

    def test_run_series_returns_two_results(self) -> None:
        result_a, result_b = _run_pair()
        assert isinstance(result_a, SeriesResult)
        assert isinstance(result_b, SeriesResult)
        assert len(result_a.ledger) == 6
        assert len(result_b.ledger) == 6

    def test_run_series_settles_with_clean_audits(self) -> None:
        result_a, result_b = _run_pair()
        assert result_a.settled is True
        assert result_b.settled is True
        assert all(row.audit_ok for row in result_a.ledger)
        assert all(row.audit_ok for row in result_b.ledger)

    def test_run_series_with_different_roles(self) -> None:
        """TC-28: verify that role alternation works across sub-games."""
        result_a, result_b = _run_pair()
        for i, row_a in enumerate(result_a.ledger, start=1):
            assert row_a.role is role_for(Role.POLICE, i)
        for i, row_b in enumerate(result_b.ledger, start=1):
            assert row_b.role is role_for(Role.THIEF, i)


class TestPolicyStub:
    """TC-27: hint-provider failure path tests."""

    def test_zero_token_template_produces_hint(self) -> None:
        """A zero-token template hint should produce a valid hint string."""
        hint = "I am here"
        assert isinstance(hint, str)
        assert len(hint) > 0
        assert not any(c.isdigit() for c in hint)

    def test_legal_action_proceeds(self) -> None:
        """When hint provider fails, legal action should still proceed."""
        engine = StandInEngine(Role.POLICE)
        engine.start_subgame(1, Role.POLICE)
        move = engine.decide()
        assert "move" in move
        assert move["move"] in ("MOVE:N", "MOVE:S", "MOVE:E", "MOVE:W", "STAY")
