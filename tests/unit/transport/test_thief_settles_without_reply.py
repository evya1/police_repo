"""A thief settles on its own knowledge, without waiting for a reply nobody owes.

The thief's sub-game can end on the move it just applied, and only the thief can see it:
the survival threshold crossed, or rules 46/47. The referee settles on what it just
received and sends NO same-numbered turn back — the pinned kit's police returns straight
out of ``netplay._play_one`` ("the survival claim already rode out on the message just
sent"). A thief that waited for that orphaned reply burned the whole ``turn_timeout`` and
then aborted the series with ``TimeoutError: timed out waiting for opponent turn 35``,
taking every later sub-game with it.

These tests pin the two halves of that: the thief settles promptly when the reply nobody
owes never comes, and silence at a step that IS still owed mid-game keeps raising — the fix
must not turn a real transport fault into a clean settle.
"""

from __future__ import annotations

import time

import pytest

from common.domain.scoring import Outcome, Role
from common.transport.series import PeerConfig
from common.transport.subgame import play_subgame

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "max_moves": 35, "survival_threshold": 35,
    "barriers_max": 14, "thief_start": [3, 3], "cop_start": [0, 0],
}


class _Budgets:
    turn_timeout = 2.0
    connect_timeout = 2.0
    poll_interval = 0.001


def _police_turn(step: int) -> dict:
    return {
        "step": step, "sender": "police", "hint": "closing in", "smell_grid": {},
        "commit": "a" * 64, "timestamp": "2026-01-01T00:00:00Z",
    }


class _KitLikePoliceChannel:
    """Answers every thief step except the one the kit's police never owes.

    `silent_from` is the first step it stops answering. At the default it mirrors the kit
    exactly: it replies all the way to step 34, then settles on our step 35 and says
    nothing more. A fully silent channel would not reproduce the bug — mid-game the thief
    genuinely IS owed each reply, and the timeout there is correct.
    """

    def __init__(self, silent_from: int = 35) -> None:
        self.silent_from = silent_from
        self.turns: list[dict] = []
        self.audits: list[dict] = []
        self._pending: list[dict] = []
        self._audit_sent = False

    def send_turn(self, message: dict) -> dict:
        self.turns.append(message)
        if int(message["step"]) < self.silent_from:
            self._pending.append(_police_turn(int(message["step"])))
        return {"ok": True}

    def send_audit(self, payload: dict) -> dict:
        self.audits.append(payload)
        return {"ok": True}

    def poll_turn(self) -> dict | None:
        return self._pending.pop(0) if self._pending else None

    def poll_audit(self) -> dict | None:
        """Answer the audit exchange once, so the timing assertion below measures the
        TURN wait and not the (correct, separate) audit wait."""
        if self._audit_sent:
            return None
        self._audit_sent = True
        return {"sender": "police", "records": [], "result_claim": "survival"}


class _ThiefEngine:
    """Minimal TurnEngine: a thief that reaches the survival threshold on its own steps."""

    def __init__(self, threshold: int = 35) -> None:
        self.threshold = threshold
        self.steps = 0

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        self.steps = 0

    def decide(self) -> dict:
        self.steps += 1
        return {"move": "STAY", "hint": "", "state": "grid=7x7;", "position": [3, 3],
                "smell_grid": {}}

    def observe_opponent(self, message: dict) -> None:
        return None

    def terminal(self) -> Outcome | None:
        return Outcome.SURVIVAL if self.steps >= self.threshold else None

    def terminal_final(self) -> dict | None:
        return None  # survival already rode the last normal step


def _config(role: Role) -> PeerConfig:
    return PeerConfig(natural_role=role, budgets=_Budgets(), terms=dict(_TERMS), seed=0)


def test_thief_settles_survival_without_the_reply_nobody_owes() -> None:
    """The reported failure: this used to raise `timed out waiting for opponent turn 35`."""
    channel = _KitLikePoliceChannel()
    started = time.monotonic()

    row = play_subgame(channel, _ThiefEngine(), _config(Role.THIEF), sub_game=1)

    assert row.role is Role.THIEF
    assert row.steps == 35, "the thief must play its full 35 steps before settling"
    # The audit still goes out: settling early must not skip what rule 35 owes.
    assert channel.audits, "no audit was sent"
    assert len(channel.turns) == 35
    # Settled on its own knowledge, not by burning the turn budget waiting for step 35.
    assert time.monotonic() - started < _Budgets.turn_timeout


def test_a_thief_still_raises_when_the_opponent_goes_silent_mid_game() -> None:
    """The guard on the fix: only the step nobody owes may be skipped.

    Silence at step 10 is a real transport fault with the game still live, and must stay a
    `TimeoutError` rather than becoming a quiet settle.
    """
    with pytest.raises(TimeoutError):
        play_subgame(
            _KitLikePoliceChannel(silent_from=10), _ThiefEngine(), _config(Role.THIEF), 1
        )
