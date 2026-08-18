"""Integration test for the inbox under deterministic fault injection.

TC-17: same seeded sequence, clean vs duplicate+reorder+drop-then-retry,
byte-identical applied sequence (NFR-1).

The flagship test runs the same sequence of turns twice — once over a clean
loopback and once over a FaultyTransport-wrapped loopback — and asserts the
inbox applies them in the same order. Duplicates are absorbed, reordering is
resolved by buffering, and drop-then-retry is transparent.
"""

from __future__ import annotations

from common.transport.faults import FaultyTransport
from common.transport.inbox import Inbox
from common.transport.loopback import pair


def _make_turn(step: int, commit: str | None = None) -> dict:
    if commit is None:
        commit = format(step, "064x")
    return {"step": step, "commit": commit, "sender": "thief", "hint": "nearby"}


def test_tc17_clean_vs_faulty_ink_indistinguishable() -> None:
    """TC-17: same sequence applied identically through clean and faulty channels."""
    sequence = [_make_turn(i) for i in range(1, 11)]

    # Clean run.
    clean_inbox = Inbox()
    for msg in sequence:
        ready = clean_inbox.offer(msg)
        assert len(ready) == 1
        assert ready[0]["step"] == msg["step"]
    clean_applied = [m["step"] for m in sequence]

    # Faulty run — duplicate every 3rd, reorder every 5th, drop-then-retry every 7th.
    a, b = pair("A", "B")
    faulty_a = FaultyTransport(
        a,
        duplicate_every=3,
        reorder_every=5,
        drop_then_retry_every=7,
    )
    faulty_inbox = Inbox()

    for msg in sequence:
        faulty_a.send_turn(msg)
    # Flush releases any held messages so the full sequence arrives.
    faulty_a.flush()

    # Drain any buffered/arrived messages from B's turn inbox.
    applied: list[dict] = []
    while True:
        raw = b.poll_turn()
        if raw is None:
            break
        ready = faulty_inbox.offer(raw)
        applied.extend(ready)

    # The applied steps should match the clean run — same order, same count.
    faulty_applied = [m["step"] for m in applied]
    assert faulty_applied == clean_applied, (
        f"Clean: {clean_applied}, Faulty: {faulty_applied}"
    )
    # Duplicates should have been absorbed.
    assert faulty_inbox.absorbed > 0, "Expected some duplicates to be absorbed"


def test_tc17_flush_releases_held_messages() -> None:
    """FaultyTransport.flush releases held messages so the inbox can apply them."""
    a, b = pair("A", "B")
    faulty_a = FaultyTransport(a, reorder_every=2)

    faulty_a.send_turn(_make_turn(1))
    faulty_a.send_turn(_make_turn(2))  # This one is held back.
    faulty_a.send_turn(_make_turn(3))  # Releases the held message; 2 and 3 arrive.

    # Without flush, message 2 might still be held.
    # With flush, everything is released.
    faulty_a.flush()

    inbox = Inbox()
    applied: list[dict] = []
    while True:
        raw = b.poll_turn()
        if raw is None:
            break
        ready = inbox.offer(raw)
        applied.extend(ready)

    steps = [m["step"] for m in applied]
    assert set(steps) == {1, 2, 3}


def test_tc17_drop_then_retry_transparent() -> None:
    """Drop-then-retry: the inbox sees the retried message, not a gap."""
    a, b = pair("A", "B")
    faulty_a = FaultyTransport(a, drop_then_retry_every=2)

    # Send 4 messages: 2 and 4 are dropped, then retried on the next send.
    for i in range(1, 5):
        faulty_a.send_turn(_make_turn(i))

    # Flush any pending drops.
    faulty_a.flush()

    inbox = Inbox()
    applied: list[dict] = []
    while True:
        raw = b.poll_turn()
        if raw is None:
            break
        ready = inbox.offer(raw)
        applied.extend(ready)

    steps = [m["step"] for m in applied]
    assert set(steps) == {1, 2, 3, 4}
