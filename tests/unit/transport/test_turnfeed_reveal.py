"""``wait_for_reveal``: the one-step ledger tolerance, and its strict default.

SPEC 3.1 lets two peers' ledgers differ by exactly one terminal step. On the thief's
FINAL lap its own step has already reached the survival threshold, so a police that
settles from that step owes no step of the same number back. Before this seam existed
the thief blocked on that never-owed reveal until ``turn_timeout`` and then aborted the
whole series with ``TimeoutError``, which is how a settled sub-game surfaced as a
timeout against a kit-conformant opponent.

The tolerance is deliberately narrow: it applies only where the caller passes a
``settled`` probe AND that probe reports an outcome. A genuinely silent opponent still
raises, so a real transport fault is never laundered into a clean settle.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Outcome
from common.transport.inbox import Inbox
from common.transport.turnfeed import wait_for_reveal


class _Budgets:
    turn_timeout = 0.05
    connect_timeout = 0.05
    poll_interval = 0.001


class _SilentChannel:
    """An opponent that never sends the awaited step."""

    def poll_turn(self) -> None:
        return None


class _OneTurnChannel:
    """Delivers exactly one turn message, then falls silent."""

    def __init__(self, message: dict) -> None:
        self._messages = [message]

    def poll_turn(self) -> object:
        return self._messages.pop(0) if self._messages else None


def _turn(step: int) -> dict:
    return {
        "step": step,
        "sender": "police",
        "hint": "closing in",
        "smell_grid": {},
        "commit": "a" * 64,
        "timestamp": "2026-01-01T00:00:00Z",
    }


def test_arrived_reveal_returns_true_and_applies() -> None:
    """The ordinary path is unchanged: the reveal lands in `applied` and we report True."""
    inbox, applied = Inbox(), {}
    arrived = wait_for_reveal(_OneTurnChannel(_turn(1)), inbox, applied, 1, _Budgets(), 7)
    assert arrived is True
    assert 1 in applied


def test_default_is_a_strict_wait_that_still_raises() -> None:
    """With no `settled` probe the function is exactly the old strict wait."""
    with pytest.raises(TimeoutError):
        wait_for_reveal(_SilentChannel(), Inbox(), {}, 35, _Budgets(), 7)


def test_settled_peer_tolerates_a_reveal_that_is_never_owed() -> None:
    """Our own state settles the sub-game, so the missing mirror step is the boundary."""
    settled = wait_for_reveal(
        _SilentChannel(), Inbox(), {}, 35, _Budgets(), 7, lambda: Outcome.SURVIVAL,
    )
    assert settled is False


def test_unsettled_peer_still_raises_on_a_silent_opponent() -> None:
    """The probe reporting None means nothing settled: this is a real fault, not a boundary."""
    with pytest.raises(TimeoutError):
        wait_for_reveal(_SilentChannel(), Inbox(), {}, 35, _Budgets(), 7, lambda: None)


def test_settled_probe_is_never_consulted_when_the_reveal_arrives() -> None:
    """The probe is a deadline-only concern; a normal turn must not invoke it."""
    calls: list[int] = []

    def probe() -> None:
        calls.append(1)
        return None

    assert wait_for_reveal(_OneTurnChannel(_turn(1)), Inbox(), {}, 1, _Budgets(), 7, probe)
    assert calls == []
