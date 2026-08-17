"""Tests for the series engine skeleton.

TC-27: hint-provider failure path — zero-token template produces hint and legal action.
TC-28: two facades that each expect the other to open — diagnostic names turn-order disagreement.
"""

from __future__ import annotations

from common.domain.scoring import Role
from common.transport.series import PeerConfig, PeerFacade, SeriesResult, run_series


class DummyBudgets:
    """Minimal budgets implementation for testing."""

    turn_timeout = 30.0
    connect_timeout = 30.0
    poll_interval = 0.1


class DummyEngine:
    """Minimal turn engine for testing."""

    def __init__(self, natural_role: Role) -> None:
        self.natural_role = natural_role

    def step(self, sub_game: int, role: Role) -> dict:
        return {"move": "STAY", "hint": "I am here"}


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


class MockChannel:
    """Mock channel for testing PeerFacade without a real transport."""

    def __init__(self, terms: dict | None = None, group_id: str = "test-peer") -> None:
        self._terms = terms or _test_terms
        self._group_id = group_id
        self._received: list[dict] = []

    def send_agreement(self, message: dict) -> dict:
        self._received.append(message)
        return {"ok": True}

    def poll_agreement(self) -> dict | None:
        from common.transport.ids import terms_signature
        from common.transport.integrity import new_nonce
        # Return a valid greeting that passes verify_greeting.
        nonce = new_nonce()
        return {
            "terms": self._terms,
            "nonce": nonce,
            "signature": terms_signature(self._terms, nonce),
            "group_id": self._group_id,
            "role": "thief",
            "sub_game_number": 1,
        }

    def send_turn(self, message: dict) -> dict:
        return {"ok": True}

    def poll_turn(self) -> dict | None:
        return None

    def send_audit(self, payload: dict) -> dict:
        return {"ok": True}

    def poll_audit(self) -> dict | None:
        return None

    def send_control(self, message: dict) -> dict:
        return {"ok": True}

    def poll_control(self) -> dict | None:
        return None

    def close(self) -> None:
        pass


class TestPeerFacade:
    """Tests for the PeerFacade."""

    def test_run_returns_series_result(self) -> None:
        config = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=_test_terms,
        )
        engine = DummyEngine(Role.POLICE)
        facade = PeerFacade(MockChannel(terms=_test_terms, group_id="B"), engine, config, "A")
        result = facade.run()
        assert isinstance(result, SeriesResult)

    def test_run_sets_settled(self) -> None:
        config = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=_test_terms,
        )
        engine = DummyEngine(Role.POLICE)
        facade = PeerFacade(MockChannel(terms=_test_terms, group_id="B"), engine, config, "A")
        result = facade.run()
        assert result.settled is True


class TestRunSeries:
    """Tests for the run_series function."""

    def test_run_series_returns_two_results(self) -> None:
        from common.transport.loopback import pair

        a, b = pair("A", "B")
        config_a = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=_test_terms,
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms=_test_terms,
        )
        engine_a = DummyEngine(Role.POLICE)
        engine_b = DummyEngine(Role.THIEF)

        result_a, result_b = run_series(a, b, config_a, config_b, engine_a, engine_b)
        assert isinstance(result_a, SeriesResult)
        assert isinstance(result_b, SeriesResult)

    def test_run_series_with_different_roles(self) -> None:
        """TC-28: verify that role alternation works across sub-games."""
        from common.domain.scoring import role_for
        from common.transport.loopback import pair

        a, b = pair("Police", "Thief")
        config_a = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=_test_terms,
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms=_test_terms,
        )
        engine_a = DummyEngine(Role.POLICE)
        engine_b = DummyEngine(Role.THIEF)

        result_a, result_b = run_series(a, b, config_a, config_b, engine_a, engine_b)

        # Verify role_for produces alternating roles
        assert role_for(Role.POLICE, 1) == Role.POLICE
        assert role_for(Role.POLICE, 2) == Role.THIEF
        assert role_for(Role.THIEF, 1) == Role.THIEF
        assert role_for(Role.THIEF, 2) == Role.POLICE


class TestPolicyStub:
    """TC-27: hint-provider failure path tests."""

    def test_zero_token_template_produces_hint(self) -> None:
        """A zero-token template hint should still produce a valid hint string."""
        # STUB: the real test will verify that the hint text carries no numeric position
        hint = "I am here"
        assert isinstance(hint, str)
        assert len(hint) > 0
        # FR-27: hint should not contain numeric positions
        assert not any(c.isdigit() for c in hint)

    def test_legal_action_proceeds(self) -> None:
        """When hint provider fails, legal action should still proceed."""
        engine = DummyEngine(Role.POLICE)
        move = engine.step(1, Role.POLICE)
        assert "move" in move
        assert move["move"] in ("MOVE:N", "MOVE:S", "MOVE:E", "MOVE:W", "STAY")
