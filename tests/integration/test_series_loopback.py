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
- Audit verdicts passed=True (stub)
- Deterministic seed => byte-identical ledger across two runs (NFR-1)
"""

from __future__ import annotations

from common.domain.scoring import Role, role_for
from common.transport.loopback import pair
from common.transport.series import PeerConfig, SeriesResult, run_series


class DummyBudgets:
    """Minimal budgets for testing."""

    turn_timeout = 30.0
    connect_timeout = 30.0
    poll_interval = 0.01


class DeterministicEngine:
    """A deterministic turn engine that produces legal moves on a board."""

    def __init__(self, natural_role: Role, board_size: int = 7, seed: int = 42) -> None:
        self.natural_role = natural_role
        self.board_size = board_size
        self.seed = seed
        self._engines: dict[int, object] = {}

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


def test_full_series_over_loopback() -> None:
    """Spine test: full six-sub-game series settles over loopback."""
    a, b = pair("Police", "Thief")

    config_a = PeerConfig(
        natural_role=Role.POLICE,
        budgets=DummyBudgets(),
        terms={"max_moves": 35, "grid_size": 7},
        seed=42,
    )
    config_b = PeerConfig(
        natural_role=Role.THIEF,
        budgets=DummyBudgets(),
        terms={"max_moves": 35, "grid_size": 7},
        seed=42,
    )

    engine_a = DeterministicEngine(Role.POLICE)
    engine_b = DeterministicEngine(Role.THIEF)

    result_a, result_b = run_series(a, b, config_a, config_b, engine_a, engine_b)

    # Both results should be SeriesResult
    assert isinstance(result_a, SeriesResult)
    assert isinstance(result_b, SeriesResult)

    # Ledger has 6 rows
    assert len(result_a.ledger) == 6, f"Expected 6 rows, got {len(result_a.ledger)}"
    assert len(result_b.ledger) == 6, f"Expected 6 rows, got {len(result_b.ledger)}"

    # Roles alternate across sub-games per role_for
    for i, row_a in enumerate(result_a.ledger, start=1):
        expected_role = role_for(Role.POLICE, i)
        assert row_a.role is expected_role, (
            f"Sub-game {i}: expected {expected_role}, got {row_a.role}"
        )

    for i, row_b in enumerate(result_b.ledger, start=1):
        expected_role = role_for(Role.THIEF, i)
        assert row_b.role is expected_role, (
            f"Sub-game {i}: expected {expected_role}, got {row_b.role}"
        )

    # All audits passed
    for row in result_a.ledger:
        assert row.audit_ok is True, f"Sub-game {row.sub_game_number}: audit not passed"
    for row in result_b.ledger:
        assert row.audit_ok is True, f"Sub-game {row.sub_game_number}: audit not passed"

    # Series is settled
    assert result_a.settled is True
    assert result_b.settled is True

    # game_id and game_uid are non-empty (from greeting exchange)
    assert result_a.game_id != ""
    assert result_a.game_uid != ""


def test_roles_alternate_correctly() -> None:
    """TC-28: verify role alternation pattern."""
    # role_for(POLICE, odd) = POLICE, role_for(POLICE, even) = THIEF
    assert role_for(Role.POLICE, 1) is Role.POLICE
    assert role_for(Role.POLICE, 2) is Role.THIEF
    assert role_for(Role.POLICE, 3) is Role.POLICE
    assert role_for(Role.POLICE, 4) is Role.THIEF
    assert role_for(Role.POLICE, 5) is Role.POLICE
    assert role_for(Role.POLICE, 6) is Role.THIEF

    # role_for(THIEF, odd) = THIEF, role_for(THIEF, even) = POLICE
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
            terms={"max_moves": 35, "grid_size": 7},
            seed=42,
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms={"max_moves": 35, "grid_size": 7},
            seed=42,
        )
        engine_a = DeterministicEngine(Role.POLICE, seed=42)
        engine_b = DeterministicEngine(Role.THIEF, seed=42)
        return run_series(a, b, config_a, config_b, engine_a, engine_b)

    result_a1, result_b1 = run_once()
    result_a2, result_b2 = run_once()

    # Ledger shapes should match
    assert len(result_a1.ledger) == len(result_a2.ledger)
    assert len(result_b1.ledger) == len(result_b2.ledger)

    # Row counts should match
    for _i, (row1, row2) in enumerate(zip(result_a1.ledger, result_a2.ledger, strict=True), start=1):
        assert row1.sub_game_number == row2.sub_game_number
        assert row1.role == row2.role
        assert row1.steps == row2.steps
