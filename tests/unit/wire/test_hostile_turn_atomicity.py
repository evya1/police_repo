"""HIGH-2: a hostile inbound turn is refused BEFORE any state changes.

The preflight in ``_wait_for_step`` is the one authoritative gate: every message is
validated against the negotiated board size before ``inbox.offer`` — the only mutation
point for delivery state — so a refusal leaves the inbox and the applied window untouched.
The role-local semantic gate in ``BrainDrivenEngine.observe_opponent`` covers what the wire
shape cannot see: an in-bounds barrier that breaks the signed quota must leave board,
session and belief exactly as they were. The Police brain + belief live on POLICE
sub-games, so the engine half of this matrix is exercised there.
"""

from __future__ import annotations

import pytest

from common.domain.rules import IllegalMoveError
from common.domain.scoring import Role
from common.transport.inbox import Inbox
from common.transport.refusals import Refused
from common.transport.subgame import _wait_for_step
from police_peer.wire.brain import BrainDrivenEngine

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 1,
    "thief_start": [3, 3], "cop_start": [0, 0],
}


class _Budgets:
    turn_timeout = 0.5
    connect_timeout = 0.5
    poll_interval = 0.001


class _ScriptedChannel:
    """Hands out pre-canned inbound messages, one per ``poll_turn``."""

    def __init__(self, *messages: object) -> None:
        self._messages = list(messages)

    def poll_turn(self) -> object:
        return self._messages.pop(0) if self._messages else None


def _turn(**overrides: object) -> dict:
    """An otherwise-valid turn from this peer's opponent (the thief)."""
    base: dict = {
        "step": 1,
        "sender": "thief",
        "hint": "running",
        "smell_grid": {},
        "commit": "a" * 64,
        "timestamp": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


HOSTILE = [
    _turn(barrier_placed=[99, 99]),
    _turn(barrier_placed=[-1, -1]),
    _turn(capture_claim=[7, 0]),
    _turn(capture_claim=[0, -1]),
    _turn(claim_response="nope"),
    _turn(claim_response=[1, 2]),
    _turn(win_claim="nope"),
    _turn(win_claim=7),
    _turn(sender="referee"),
    _turn(shadow_position=[1, 2]),
    [],
    ["step", 1],
]


def _inbox_snapshot(inbox: Inbox) -> tuple:
    return (dict(inbox.played), dict(inbox.buffered), inbox.next_step, inbox.absorbed)


@pytest.mark.parametrize("message", HOSTILE)
def test_hostile_turn_refused_with_zero_mutation(message: object) -> None:
    inbox, applied = Inbox(), {}
    before = _inbox_snapshot(inbox)
    with pytest.raises(Refused) as excinfo:
        _wait_for_step(_ScriptedChannel(message), inbox, applied, 1, _Budgets(), 7)
    assert excinfo.value.code == "SPAR-N11"
    assert applied == {}
    assert _inbox_snapshot(inbox) == before


def test_valid_turn_still_applies_once() -> None:
    inbox, applied = Inbox(), {}
    _wait_for_step(
        _ScriptedChannel(_turn(barrier_placed=[0, 6])), inbox, applied, 1, _Budgets(), 7,
    )
    assert applied[1]["barrier_placed"] == [0, 6]
    assert inbox.next_step == 2


def _started_engine() -> BrainDrivenEngine:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, terms=_TERMS, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    return engine


def _engine_snapshot(engine: BrainDrivenEngine) -> tuple:
    game, belief = engine._session.engine, engine._belief
    return (
        list(game.barriers), game.opponent_barriers, game.barriers_placed,
        game.position, game.step,
        [row[:] for row in belief.as_matrix()], set(belief.allowed_cells),
    )


def test_quota_breaking_barrier_leaves_board_session_and_belief_unchanged() -> None:
    """In bounds, so wire-valid — but the signed quota is 1, so the second is illegal."""
    engine = _started_engine()
    engine.observe_opponent(_turn(barrier_placed=[0, 6]))
    before = _engine_snapshot(engine)

    with pytest.raises(IllegalMoveError):
        engine.observe_opponent(_turn(step=2, barrier_placed=[6, 0], hint="second"))

    assert _engine_snapshot(engine) == before


def test_off_board_barrier_reaching_observe_opponent_mutates_nothing() -> None:
    engine = _started_engine()
    before = _engine_snapshot(engine)
    with pytest.raises(IllegalMoveError):
        engine.observe_opponent(_turn(barrier_placed=[9, 9]))
    assert _engine_snapshot(engine) == before


def test_valid_barrier_is_applied_and_excluded_exactly_once() -> None:
    engine = _started_engine()
    engine.observe_opponent(_turn(barrier_placed=[0, 6]))
    game = engine._session.engine
    assert game.barriers == [(0, 6)]
    assert game.opponent_barriers == 1
    assert engine._belief.prob((0, 6)) == 0.0
    assert (0, 6) not in engine._belief.allowed_cells
