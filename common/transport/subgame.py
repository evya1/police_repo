"""Per-subgame turn exchange, FSM transitions, and mutual audit.

Strict thief-first alternation: thief sends first; police waits for thief step 1 before
computing its first move; each subsequent half-turn pairs commits and reveals with FSM
state tracking. Survival occurs when thief reaches survival_threshold; early capture
terminates both peers cleanly without deadlock: a thief that saw its own capture
(rules 46/47 — a fact only the thief can see) owes one last sealed STAY carrying the
concession, and the police that settles from it answers with a plain sealed STAY, so
both ledgers record the same final step and the audits corroborate one outcome
instead of forking (rule 35).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from common.domain.scoring import Outcome, Role, role_for, score_for, settled_outcome
from common.transport.audit import audit_records
from common.transport.inbox import Inbox
from common.transport.refusals import Refused
from common.transport.series import PeerConfig, SeriesRow, TurnEngine
from common.transport.state import PeerState, PeerStateMachine
from common.transport.validators import validate_turn


def play_subgame(channel, engine: TurnEngine, config: PeerConfig, sub_game: int) -> SeriesRow:
    """Play one sub-game: strict thief-first alternation, mutual audit."""
    terms = config.terms or {}
    max_steps = int(terms.get("max_steps", 35))
    survival_threshold = int(terms.get("survival_threshold", max_steps))
    max_moves = int(terms.get("max_moves", max_steps))
    if max_moves != survival_threshold or max_steps != survival_threshold:
        raise ValueError(
            f"divergent max_moves/max_steps ({max_steps}) and survival_threshold "
            f"({survival_threshold}) refused (OPEN-011)"
        )

    role = role_for(config.natural_role, sub_game)
    is_thief = role is Role.THIEF
    inbox = Inbox()
    applied: dict[int, dict] = {}
    applied_seen: set[int] = set()
    our_records: list[dict] = []

    machine = PeerStateMachine()
    engine.start_subgame(sub_game, role, terms=terms)

    if not is_thief:
        # Police honours thief-first (FR-18): hold thief's first move before sending own
        _wait_for_step(channel, inbox, applied, 1, config.budgets)

    flush = getattr(channel, "flush", None)
    terminal: Outcome | None = None

    for lap in range(1, max_steps + 1):
        machine.to(PeerState.COMPUTING_MOVE)
        message, record = _our_move(engine, role, is_thief, lap, sub_game)

        machine.to(PeerState.COMMITTING)
        channel.send_turn(message)
        our_records.append(record)

        if flush is not None:
            flush()

        machine.to(PeerState.AWAITING_REVEAL)
        _wait_for_step(channel, inbox, applied, lap, config.budgets)

        machine.to(PeerState.VERIFYING)
        _observe_once(applied, applied_seen, engine, lap)

        machine.to(PeerState.WAITING_FOR_OPPONENT)
        terminal = engine.terminal()
        if terminal is not None:
            # In-loop settle. A thief owes the rules-46/47 concession (step lap+1);
            # a police settles silently — the signal rode the thief's own step, and an
            # extra police step would make the ledgers diverge.
            if is_thief:
                _settle_final(channel, machine, engine, role, is_thief, lap + 1, our_records, flush)
            break

        # For strict alternation after step 1: police pre-waits for thief's next step.
        # A terminal arriving there settles with a sealed STAY (step lap+1) so both
        # ledgers record the same final step; the thief was still owed that step.
        if not is_thief and lap < max_steps:
            _wait_for_step(channel, inbox, applied, lap + 1, config.budgets)
            _observe_once(applied, applied_seen, engine, lap + 1)
            terminal = engine.terminal()
            if terminal is not None:
                _settle_final(channel, machine, engine, role, is_thief, lap + 1, our_records, flush)
                break

    if terminal is None and not is_thief:
        # A thief captured on the FINAL lap owes the max_steps+1 concession; a silent
        # thief stays TECHNICAL_LOSS. The police never seals past the physics ceiling.
        try:
            _wait_for_step(channel, inbox, applied, max_steps + 1, config.budgets)
            _observe_once(applied, applied_seen, engine, max_steps + 1)
            terminal = engine.terminal()
        except TimeoutError:
            pass

    if terminal is None:
        terminal = Outcome.TECHNICAL_LOSS

    channel.send_audit(_audit_payload(role, our_records, terminal))
    opponent_audit = _wait_audit(channel, config.budgets)
    if opponent_audit is None:
        audit_ok, audits_present = False, False
    else:
        result = audit_records(
            opponent_audit.get("records", []),
            inbox.played,
            terms,
            our_records=our_records,
            our_result_claim=terminal.value,
            opponent_result_claim=opponent_audit.get("result_claim"),
        )
        audit_ok, audits_present = result.passed, True
    final_outcome, _ = settled_outcome(terminal, audits_present=audits_present, audits_passed=audit_ok)
    return SeriesRow(
        sub_game_number=sub_game,
        role=role,
        outcome=final_outcome,
        steps=len(our_records),
        score_police=score_for(final_outcome, Role.POLICE),
        score_thief=score_for(final_outcome, Role.THIEF),
        audit_ok=audit_ok,
    )


def _observe_once(applied: dict[int, dict], seen: set[int], engine: TurnEngine, step: int) -> None:
    """Observe an applied step exactly once — observe_opponent is not idempotent."""
    if step in seen:
        return
    seen.add(step)
    engine.observe_opponent(applied[step])


def _seal_turn(decision: dict, role: Role, is_thief: bool, step: int) -> tuple[dict, dict]:
    """Seal a decision into (public turn message, sealed record)."""
    from common.transport.canonical import commit as hash_commit
    from common.transport.integrity import new_nonce

    nonce = new_nonce()
    payload = dict(decision)
    payload["step"] = step
    payload["sender"] = role.value
    payload["intent"] = "evade" if is_thief else "chase"
    payload["timestamp"] = datetime.now(UTC).isoformat()

    commit = hash_commit(payload, nonce)
    record = dict(payload, nonce=nonce, commit=commit)

    public_keys = {
        "step", "sender", "hint", "smell_grid", "barrier_placed",
        "capture_claim", "claim_response", "win_claim", "timestamp",
    }
    message = {key: payload[key] for key in public_keys if key in payload}
    message["commit"] = commit
    return message, record


def _our_move(engine, role: Role, is_thief: bool, lap: int, sub_game: int) -> tuple[dict, dict]:
    """Ask the engine for a move; return (turn message, sealed record)."""
    return _seal_turn(engine.decide(), role, is_thief, lap)


def _terminal_final(engine, role: Role, is_thief: bool, step: int) -> tuple[dict, dict] | None:
    """The sealed game-ending final, or None if this engine owes none."""
    fn = getattr(engine, "terminal_final", None)
    if fn is None:
        return None
    payload = fn()
    return None if payload is None else _seal_turn(payload, role, is_thief, step)


def _settle_final(
    channel, machine, engine, role: Role, is_thief: bool, step: int,
    our_records: list[dict], flush,
) -> None:
    """Send the settled final step (COMPUTING_MOVE -> COMMITTING from WAITING_FOR_OPPONENT)."""
    final = _terminal_final(engine, role, is_thief, step)
    if final is None:
        return
    machine.to(PeerState.COMPUTING_MOVE)
    machine.to(PeerState.COMMITTING)
    message, record = final
    channel.send_turn(message)
    our_records.append(record)
    if flush is not None:
        flush()


def _audit_payload(role: Role, our_records: list[dict], terminal: Outcome) -> dict:
    """Seal the step-0 identity record and pack our audit payload (FR-19, FR-42)."""
    from common.transport.canonical import commit as hash_commit
    from common.transport.integrity import new_nonce

    nonce = new_nonce()
    step0_payload = {"step": 0, "sender": role.value, "intent": "declare"}
    step0 = dict(step0_payload, nonce=nonce, commit=hash_commit(step0_payload, nonce))
    records = [step0] + our_records
    return {
        "records": records,
        "nonces": [r["nonce"] for r in records],
        "result_claim": terminal.value,
    }


def _wait_for_step(channel, inbox: Inbox, applied: dict[int, dict], step: int, budgets) -> None:
    """Feed the turn channel into the inbox until the opponent's `step` move has applied.

    Every inbound message is validated (FR-25) before it ever reaches ``inbox.offer`` —
    the only mutation point for delivery state — so a malformed turn is refused with
    zero partial mutation instead of corrupting the reorder window.
    """
    deadline = time.monotonic() + budgets.turn_timeout
    while time.monotonic() < deadline:
        while (msg := channel.poll_turn()) is not None:
            verdict = validate_turn(msg)
            if verdict != "accept":
                raise Refused("SPAR-N11", verdict)
            for ready in inbox.offer(msg):
                applied[int(ready["step"])] = ready
        if step in applied:
            return
        time.sleep(budgets.poll_interval)
    raise TimeoutError(f"timed out waiting for opponent turn {step}")


def _wait_audit(channel, budgets) -> dict | None:
    """Poll for the opponent's audit payload until deadline."""
    deadline = time.monotonic() + budgets.turn_timeout
    while time.monotonic() < deadline:
        msg = channel.poll_audit()
        if msg is not None:
            return msg
        time.sleep(budgets.poll_interval)
    return None
