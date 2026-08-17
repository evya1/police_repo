"""TC-17 (final): clean vs fault-injected seeded series ⇒ byte-identical ledger.

The flagship receiver-contract test at the series level. The same seeded six-sub-game
series runs twice — once over a clean loopback and once over a ``FaultyTransport``
(duplicate + reorder + drop-then-retry on the turn channel) — and the outcome ledgers,
**including the audit verdicts**, are asserted byte-identical (NFR-1, US-MCP-003).

The faults change how the turns arrive (duplicates absorbed, a bounded reorder window
re-applied in sequence, a dropped-then-retried turn delivered once) but never who won,
never the steps, and never the mutual-audit verdict. The real three-layer audit binds
the reveals to the stored commitments, so the verdicts are part of the comparison.
"""

from __future__ import annotations

from common.domain.scoring import Role, role_for
from common.transport.canonical import canonical_bytes
from common.transport.faults import FaultyTransport
from common.transport.loopback import pair
from common.transport.series import PeerConfig, SeriesResult, run_series

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


class _Budgets:
    turn_timeout = 15.0
    connect_timeout = 15.0
    poll_interval = 0.005


class _Engine:
    """Deterministic stand-in engine: a fresh local engine per move, first legal move."""

    def __init__(self, natural_role: Role, board_size: int = 7) -> None:
        self.natural_role = natural_role
        self.board_size = board_size

    def step(self, sub_game: int, role: Role) -> dict:
        from common.domain.board import Board
        from common.domain.rules import GameEngine

        board = Board(size=self.board_size)
        position = (0, 0) if role is Role.POLICE else (3, 3)
        engine = GameEngine(board=board, role=role, position=position)
        legal = engine.legal_moves()
        move = legal[0] if legal else "STAY"
        engine.apply_own_move(move)
        return {"move": move, "hint": "I am here", "step": 0, "state": engine.state_string()}


def _configs() -> tuple[PeerConfig, PeerConfig]:
    return (
        PeerConfig(natural_role=Role.POLICE, budgets=_Budgets(), terms=_full_terms, seed=42),
        PeerConfig(natural_role=Role.THIEF, budgets=_Budgets(), terms=_full_terms, seed=42),
    )


def _run_clean() -> tuple[SeriesResult, SeriesResult]:
    a, b = pair("Police", "Thief")
    config_a, config_b = _configs()
    return run_series(a, b, config_a, config_b, _Engine(Role.POLICE), _Engine(Role.THIEF))


def _run_faulty() -> tuple[SeriesResult, SeriesResult]:
    ta, tb = pair("Police", "Thief")
    # Hazards on both directions at different periods (the reference pairing).
    faulty_a = FaultyTransport(ta, duplicate_every=3, reorder_every=5, drop_then_retry_every=7)
    faulty_b = FaultyTransport(tb, duplicate_every=4, reorder_every=6, drop_then_retry_every=9)
    config_a, config_b = _configs()
    return run_series(faulty_a, faulty_b, config_a, config_b, _Engine(Role.POLICE), _Engine(Role.THIEF))


def _ledger_bytes(result: SeriesResult) -> bytes:
    """The outcome ledger as canonical bytes — rows, scores, and the audit verdicts."""
    rows = [
        {
            "sub_game_number": row.sub_game_number,
            "role": row.role.value,
            "outcome": row.outcome.value,
            "steps": row.steps,
            "score_police": row.score_police,
            "score_thief": row.score_thief,
            "audit_ok": row.audit_ok,
        }
        for row in result.ledger
    ]
    return canonical_bytes(
        {"rows": rows, "settled": result.settled, "settled_outcome": result.settled_outcome.value}
    )


def test_tc17_clean_vs_faulty_ledger_byte_identical() -> None:
    clean_a, clean_b = _run_clean()
    faulty_a, faulty_b = _run_faulty()
    assert _ledger_bytes(clean_a) == _ledger_bytes(faulty_a)
    assert _ledger_bytes(clean_b) == _ledger_bytes(faulty_b)


def test_tc17_faulty_audits_still_pass_and_settle() -> None:
    faulty_a, faulty_b = _run_faulty()
    assert len(faulty_a.ledger) == 6
    assert len(faulty_b.ledger) == 6
    for i, row_a in enumerate(faulty_a.ledger, start=1):
        assert row_a.role is role_for(Role.POLICE, i)
        assert row_a.audit_ok is True
    for i, row_b in enumerate(faulty_b.ledger, start=1):
        assert row_b.role is role_for(Role.THIEF, i)
        assert row_b.audit_ok is True
    assert faulty_a.settled is True
    assert faulty_b.settled is True
