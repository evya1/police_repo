"""The wire schema's null contract: "<shape> ... or null" must hold end to end.

``validate_turn`` documents every optional turn field as accepting an explicit
null, so a conformant encoder may always emit the key. The semantic layer must
therefore gate on the VALUE, not on key presence — keying off presence made such
a turn crash on ``_as_cell(None)`` AFTER the barrier had been absorbed, i.e. a
partially applied turn, which is precisely what the preflight exists to prevent
(FR-25). Our own peers never emit explicit nulls, so only a foreign encoder
reaches this path; that is exactly why it needs its own regression file.

This repository already gated on the value, so nothing here changes production
behaviour — the file exists to pin both peers to one contract so they cannot
drift apart again on identical role-agnostic wire input.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Role
from common.transport.validators import validate_turn
from police_peer.wire.brain import BrainDrivenEngine

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}

#: Every optional field, alone and combined — including the barrier pairing that
#: made the original crash non-atomic.
EXPLICIT_NULLS = [
    {"capture_claim": None},
    {"barrier_placed": None},
    {"claim_response": None},
    {"win_claim": None},
    {"barrier_placed": [5, 5], "capture_claim": None},
    {"barrier_placed": None, "capture_claim": None,
     "claim_response": None, "win_claim": None},
]


def _turn(**overrides: object) -> dict:
    base: dict = {
        "step": 1,
        "sender": "thief",
        "hint": "closing in",
        "smell_grid": {},
        "commit": "a" * 64,
        "timestamp": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _started_engine() -> BrainDrivenEngine:
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=1, terms=_TERMS, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    return engine


@pytest.mark.parametrize("optionals", EXPLICIT_NULLS)
def test_explicit_null_optionals_are_accepted_by_the_preflight(optionals: dict) -> None:
    assert validate_turn(_turn(**optionals), board_size=7) == "accept"


@pytest.mark.parametrize("optionals", EXPLICIT_NULLS)
def test_explicit_null_optionals_never_reach_the_engine_as_a_crash(optionals: dict) -> None:
    """A turn the validator accepts must not blow up the semantic layer."""
    _started_engine().observe_opponent(_turn(**optionals))


def test_explicit_null_claim_alongside_a_barrier_stays_atomic() -> None:
    """The regression: the barrier was absorbed, then _as_cell(None) killed the series."""
    engine = _started_engine()
    engine.observe_opponent(_turn(barrier_placed=[5, 5], capture_claim=None))
    game = engine._session.engine
    assert game.barriers == [(5, 5)]
    assert game.opponent_barriers == 1
