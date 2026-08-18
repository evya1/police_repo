"""One sub-game: thief-first sealing, at-least-once delivery, then the mutual audit.

Split from ``series.py`` to respect the 150-logical-line cap. A sub-game seals a fixed
number of half-turns (thief first, FR-18) and exchanges them over the turn channel,
then runs the audit exchange that settles it.

The send phase is never gated on a receive: each side seals and sends all of its moves,
then flushes any fault-injected held messages, then waits for the opponent's final move.
Gating a send on a possibly-held message is how a reorder fault deadlocks a strict
alternation — the held message is released only by the next send. Delivery is
at-least-once (``Inbox``): exact duplicates are absorbed and a bounded reorder window
applies in sequence, so a fault-injected channel changes nothing about the outcome.
A failed audit settles ``TAMPER_FORFEIT`` — both sides zeroed, no repair path (FR-29).
"""

from __future__ import annotations

import time

from common.domain.scoring import Outcome, Role, role_for, score_for, settled_outcome
from common.transport.audit import audit_records
from common.transport.inbox import Inbox
from common.transport.series import LAPS_PER_SUBGAME, PeerConfig, SeriesRow, TurnEngine


def play_subgame(channel, engine: TurnEngine, config: PeerConfig, sub_game: int) -> SeriesRow:
    """Play one sub-game: thief-first sealing, at-least-once exchange, mutual audit."""
    role = role_for(config.natural_role, sub_game)
    is_thief = role is Role.THIEF
    inbox = Inbox()
    applied: dict[int, dict] = {}
    our_records: list[dict] = []

    if not is_thief:
        # The police honours thief-first (FR-18): it must hold the thief's first sealed
        # move before it sends anything of its own.
        _wait_for_step(channel, inbox, applied, 1, config.budgets)

    for lap in range(1, LAPS_PER_SUBGAME + 1):
        message, record = _our_move(engine, role, is_thief, lap, sub_game)
        channel.send_turn(message)
        our_records.append(record)

    # Release fault-injected held turns before waiting on the opponent's final move, so a
    # held last move can never gate the mutual wait (no-op on a clean channel).
    flush = getattr(channel, "flush", None)
    if flush is not None:
        flush()

    _wait_for_step(channel, inbox, applied, LAPS_PER_SUBGAME, config.budgets)

    terminal = Outcome.SURVIVAL if is_thief else Outcome.CAPTURE
    channel.send_audit(_audit_payload(role, our_records, terminal))
    opponent_audit = _wait_audit(channel, config.budgets)
    if opponent_audit is None:
        audit_ok, audits_present = False, False
    else:
        result = audit_records(opponent_audit.get("records", []), inbox.played, config.terms)
        audit_ok, audits_present = result.passed, True
    final_outcome, _ = settled_outcome(terminal, audits_present=audits_present, audits_passed=audit_ok)
    return SeriesRow(
        sub_game_number=sub_game,
        role=role,
        outcome=final_outcome,
        steps=len(our_records) + len(applied),
        score_police=score_for(final_outcome, Role.POLICE),
        score_thief=score_for(final_outcome, Role.THIEF),
        audit_ok=audit_ok,
    )


def _our_move(engine, role: Role, is_thief: bool, lap: int, sub_game: int) -> tuple[dict, dict]:
    """Ask the engine for a move; return (turn message, sealed record).

    The turn message carries only the commit and the public hint — the nonce and the sealed
    state stay hidden until the audit reveals them (SEC-004, NFR-6).
    """
    from common.transport.canonical import commit as hash_commit
    from common.transport.integrity import new_nonce

    nonce = new_nonce()
    payload = dict(engine.step(sub_game, role))
    payload["step"] = lap
    payload["sender"] = role.value
    payload["intent"] = "evade" if is_thief else "chase"
    commit = hash_commit(payload, nonce)
    record = dict(payload, nonce=nonce, commit=commit)
    message = {key: payload[key] for key in ("step", "sender", "hint")}
    message["commit"] = commit
    return message, record


def _audit_payload(role: Role, our_records: list[dict], terminal: Outcome) -> dict:
    """Seal the step-0 identity record and pack our audit payload (FR-19, FR-42)."""
    from common.transport.canonical import commit as hash_commit
    from common.transport.integrity import new_nonce

    nonce = new_nonce()
    step0_payload = {"step": 0, "sender": role.value, "intent": "declare"}
    step0 = dict(step0_payload, nonce=nonce, commit=hash_commit(step0_payload, nonce))
    records = [step0] + our_records
    return {"records": records, "nonces": [r["nonce"] for r in records], "result_claim": terminal.value}


def _wait_for_step(channel, inbox: Inbox, applied: dict[int, dict], step: int, budgets) -> None:
    """Feed the turn channel into the inbox until the opponent's `step` move has applied."""
    deadline = time.monotonic() + budgets.turn_timeout
    while time.monotonic() < deadline:
        while (msg := channel.poll_turn()) is not None:
            for ready in inbox.offer(msg):
                applied[int(ready["step"])] = ready
        if step in applied:
            return
        time.sleep(budgets.poll_interval)
    raise TimeoutError(f"opponent turn for step {step} not received in budget")


def _wait_audit(channel, budgets) -> dict | None:
    """Poll the audit channel until the opponent's audit arrives (or the budget expires)."""
    deadline = time.monotonic() + budgets.turn_timeout
    while time.monotonic() < deadline:
        audit = channel.poll_audit()
        if audit is not None:
            return audit
        time.sleep(budgets.poll_interval)
    return None
