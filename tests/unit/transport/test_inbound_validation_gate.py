"""Failing-first test: inbound validation runs before inbox/state mutation.

Item 7 of the repair task's required tests (FR-25): a malformed timestamp,
commit, coordinate, scent value, or sender causes a refusal with zero
partial mutation of the Inbox's delivery state.
"""

from __future__ import annotations

import pytest

from common.transport.inbox import Inbox
from common.transport.refusals import Refused
from common.transport.turnfeed import wait_for_step

_BOARD_SIZE = 7  # the negotiated board size; the gate never assumes a hard-coded 7


class _Budgets:
    turn_timeout = 0.05
    poll_interval = 0.001


class _FakeChannel:
    def __init__(self, msgs: list[dict]) -> None:
        self._msgs = list(msgs)

    def poll_turn(self) -> dict | None:
        return self._msgs.pop(0) if self._msgs else None


def _valid_turn(**overrides: object) -> dict:
    base: dict = {
        "step": 1, "sender": "thief", "hint": "hi", "smell_grid": {"0,0": 0.5},
        "commit": "a" * 64, "timestamp": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "bad_field,bad_value",
    [
        ("timestamp", ""),
        ("commit", "too-short"),
        ("sender", ""),
        ("smell_grid", {"not-a-cell": "not-a-number"}),
    ],
)
def test_malformed_field_refused_before_inbox_mutation(bad_field: str, bad_value: object) -> None:
    bad = _valid_turn(**{bad_field: bad_value})
    inbox = Inbox()
    applied: dict[int, dict] = {}

    with pytest.raises(Refused) as excinfo:
        wait_for_step(_FakeChannel([bad]), inbox, applied, 1, _Budgets(), _BOARD_SIZE)

    assert excinfo.value.code == "SPAR-N11"
    assert applied == {}
    assert inbox.played == {}
    assert inbox.next_step == 1
    assert inbox.buffered == {}


def test_valid_turn_applies_normally() -> None:
    good = _valid_turn()
    inbox = Inbox()
    applied: dict[int, dict] = {}
    wait_for_step(_FakeChannel([good]), inbox, applied, 1, _Budgets(), _BOARD_SIZE)
    assert 1 in applied
    assert inbox.played[1] == good["commit"]


def test_unknown_extension_keys_are_tolerated() -> None:
    good = _valid_turn(future_field="anything")
    inbox = Inbox()
    applied: dict[int, dict] = {}
    wait_for_step(_FakeChannel([good]), inbox, applied, 1, _Budgets(), _BOARD_SIZE)
    assert 1 in applied
    assert applied[1]["future_field"] == "anything"
