"""Unit tests for the FSM-driven subgame driver (D5: failure parity with legacy)."""

from __future__ import annotations

import threading

import pytest

from common.domain.scoring import Role, role_for
from common.transport.series import PeerConfig
from common.transport.subgame import play_subgame
from common.transport.subgame_fsm import play_subgame_fsm


class DummyBudgets:
    """Minimal budgets for testing."""

    turn_timeout = 30.0
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


class DeterministicEngine:
    """A deterministic turn engine that produces legal moves on a board."""

    def __init__(self, natural_role: Role, board_size: int = 7) -> None:
        self.natural_role = natural_role
        self.board_size = board_size

    def _fresh_engine(self, sub_game: int):
        """Create a fresh GameEngine for the given sub-game."""
        from common.domain.board import Board
        from common.domain.rules import GameEngine

        role = role_for(self.natural_role, sub_game)
        board = Board(size=self.board_size)
        position = (0, 0) if role is Role.POLICE else (3, 3)
        return GameEngine(board=board, role=role, position=position)

    def step(self, sub_game: int, role: Role) -> dict:
        """Return a deterministic move dict."""
        engine = self._fresh_engine(sub_game)
        legal = engine.legal_moves()
        move = legal[0] if legal else "STAY"
        engine.apply_own_move(move)
        return {
            "move": move,
            "hint": "I am here",
            "step": 0,
            "state": engine.state_string(),
        }


def _run_subgame_pair(channel_a, channel_b, engine_a, engine_b, config_a, config_b,
                      driver) -> tuple[object, object]:
    """Run one sub-game on both sides of a loopback pair using the given driver."""
    result_a = result_b = None
    errors: list[Exception] = []

    def run_a() -> None:
        nonlocal result_a
        try:
            result_a = driver(channel_a, engine_a, config_a, 1)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def run_b() -> None:
        nonlocal result_b
        try:
            result_b = driver(channel_b, engine_b, config_b, 1)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    thread_a = threading.Thread(target=run_a, daemon=True)
    thread_b = threading.Thread(target=run_b, daemon=True)
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=30)
    thread_b.join(timeout=30)
    if errors:
        raise RuntimeError(f"sub-game errors: {errors}")
    return result_a, result_b


@pytest.mark.parametrize("sub_game", (1, 2))
def test_fsm_driver_matches_legacy_row_for_row(sub_game: int) -> None:
    """Both drivers produce byte-identical SeriesRow fields for the same sub-game."""
    from common.transport.loopback import pair

    config_a = PeerConfig(natural_role=Role.POLICE, budgets=DummyBudgets(), terms=_full_terms, seed=42)
    config_b = PeerConfig(natural_role=Role.THIEF, budgets=DummyBudgets(), terms=_full_terms, seed=42)
    engine_a = DeterministicEngine(Role.POLICE)
    engine_b = DeterministicEngine(Role.THIEF)

    ch_legacy_a, ch_legacy_b = pair("Police", "Thief")
    row_legacy_a, _row_legacy_b = _run_subgame_pair(
        ch_legacy_a, ch_legacy_b, engine_a, engine_b, config_a, config_b, play_subgame
    )

    ch_fsm_a, ch_fsm_b = pair("Police", "Thief")
    row_fsm_a, _row_fsm_b = _run_subgame_pair(
        ch_fsm_a, ch_fsm_b, engine_a, engine_b, config_a, config_b, play_subgame_fsm
    )

    assert row_legacy_a.sub_game_number == row_fsm_a.sub_game_number
    assert row_legacy_a.role == row_fsm_a.role
    assert row_legacy_a.outcome == row_fsm_a.outcome
    assert row_legacy_a.steps == row_fsm_a.steps
    assert row_legacy_a.score_police == row_fsm_a.score_police
    assert row_legacy_a.score_thief == row_fsm_a.score_thief
    assert row_legacy_a.audit_ok == row_fsm_a.audit_ok


class _TightBudgets:
    """Tight budgets for the deadline test — pins D5 without a 30s wait."""

    turn_timeout = 0.05
    connect_timeout = 30.0
    poll_interval = 0.01


def test_fsm_driver_raises_like_legacy_on_deadline() -> None:
    """Both drivers raise TimeoutError when the opponent never sends a turn (D5)."""
    from common.transport.loopback import pair

    class DropTurnChannel:
        """A channel wrapper that drops all turn messages."""

        def __init__(self, inner):
            self._inner = inner

        def send_turn(self, message):
            # Silently drop — opponent never receives.
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
    engine = DeterministicEngine(Role.POLICE)

    with pytest.raises(TimeoutError):
        play_subgame(ch_a_dropped, engine, config, 1)
    with pytest.raises(TimeoutError):
        play_subgame_fsm(ch_a_dropped, engine, config, 1)
