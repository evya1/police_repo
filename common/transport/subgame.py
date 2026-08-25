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

from collections.abc import Callable

from common.domain.scoring import Outcome, Role, role_for, score_for, settled_outcome
from common.transport.audit import audit_records
from common.transport.audit_wire import AuditWireAdapter, default_audit_wire
from common.transport.inbox import Inbox
from common.transport.replay_evidence import SubgameReplayEvidence, capture_subgame_evidence
from common.transport.series import PeerConfig, SeriesRow, TurnEngine
from common.transport.state import PeerState, PeerStateMachine
from common.transport.turnfeed import (
    reconcile_subgame_boundary,
    wait_audit,
    wait_for_step,
)
from common.transport.turnseal import audit_payload, seal_turn, settle_final


def play_subgame(
    channel,
    engine: TurnEngine,
    config: PeerConfig,
    sub_game: int,
    *,
    evidence_sink: Callable[[SubgameReplayEvidence], None] | None = None,
    audit_wire: AuditWireAdapter | None = None,
) -> SeriesRow:
    """Play one sub-game: strict thief-first alternation, mutual audit."""
    terms = config.terms or {}
    wire = audit_wire if audit_wire is not None else default_audit_wire()
    max_steps = int(terms.get("max_steps", 35))
    survival_threshold = int(terms.get("survival_threshold", max_steps))
    max_moves = int(terms.get("max_moves", max_steps))
    if max_moves != survival_threshold or max_steps != survival_threshold:
        raise ValueError(
            f"divergent max_moves/max_steps ({max_steps}) and survival_threshold "
            f"({survival_threshold}) refused by the production termination contract"
        )

    board_size = int(terms.get("board_size", 7))
    role = role_for(config.natural_role, sub_game)
    is_thief = role is Role.THIEF
    inbox = Inbox()
    applied: dict[int, dict] = {}
    applied_seen: set[int] = set()
    our_records: list[dict] = []

    machine = PeerStateMachine()
    engine.start_subgame(sub_game, role, terms=terms)

    # Rule 35: the previous sub-game's owed final STAY is still in the transport.
    reconcile_subgame_boundary(channel, inbox, applied, board_size)

    if not is_thief:
        # Police honours thief-first (FR-18): hold thief's first move before sending own
        wait_for_step(channel, inbox, applied, 1, config.budgets, board_size)

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

        # The THIEF's game can end on the move it just applied, and only it knows:
        # the survival threshold crossed, a barrier on its own cell or no legal move
        # (rules 46/47), or an answered cop claim. In every one the referee settles
        # on what it just received and owes NO same-numbered reply — the reference's
        # settling POLICE sends no terminal turn (``netplay._play_one`` ->
        # ``terminal_message`` is nil without a concession/answer/survival). Waiting
        # for an orphaned next opponent turn deadlocks a sub-game the thief already
        # won, so settle here on our own knowledge, before the wait.
        if is_thief and (terminal := engine.terminal()) is not None:
            settle_final(channel, machine, engine, role, is_thief, lap + 1, our_records, flush)
            break

        machine.to(PeerState.AWAITING_REVEAL)
        wait_for_step(channel, inbox, applied, lap, config.budgets, board_size)

        machine.to(PeerState.VERIFYING)
        _observe_once(applied, applied_seen, engine, lap)

        machine.to(PeerState.WAITING_FOR_OPPONENT)
        terminal = engine.terminal()
        if terminal is not None:
            # In-loop settle. A thief owes the rules-46/47 concession (step lap+1);
            # a police settles silently — the signal rode the thief's own step, and an
            # extra police step would make the ledgers diverge.
            if is_thief:
                settle_final(channel, machine, engine, role, is_thief, lap + 1, our_records, flush)
            break

        # For strict alternation after step 1: police pre-waits for thief's next step.
        # A terminal arriving there settles with a sealed STAY (step lap+1) so both
        # ledgers record the same final step; the thief was still owed that step.
        if not is_thief and lap < max_steps:
            wait_for_step(channel, inbox, applied, lap + 1, config.budgets, board_size)
            _observe_once(applied, applied_seen, engine, lap + 1)
            terminal = engine.terminal()
            if terminal is not None:
                settle_final(channel, machine, engine, role, is_thief, lap + 1, our_records, flush)
                break

    if terminal is None and not is_thief:
        # A thief captured on the FINAL lap owes the max_steps+1 concession; a silent
        # thief stays TECHNICAL_LOSS. The police never seals past the physics ceiling.
        try:
            wait_for_step(channel, inbox, applied, max_steps + 1, config.budgets, board_size)
            _observe_once(applied, applied_seen, engine, max_steps + 1)
            terminal = engine.terminal()
        except TimeoutError:
            pass

    if terminal is None:
        terminal = Outcome.TECHNICAL_LOSS

    audit = audit_payload(role, our_records, terminal)
    channel.send_audit(wire.outbound(sender=role.value, audit=audit))
    # Normalize BEFORE the verifier: `audit_records` decodes strictly and is left
    # untouched, so a nested kit record must arrive flat or it reads as malformed.
    opponent_audit = wire.inbound(wait_audit(channel, config.budgets))
    opponent_records_raw: object = []
    opponent_result_claim: str | None = None
    if opponent_audit is None:
        audit_ok, audits_present = False, False
    else:
        opponent_records_raw = opponent_audit.get("records", [])
        opponent_result_claim = opponent_audit.get("result_claim")
        result = audit_records(
            opponent_records_raw,
            inbox.played,
            terms,
            our_records=our_records,
            our_result_claim=terminal.value,
            opponent_result_claim=opponent_result_claim,
        )
        audit_ok, audits_present = result.passed, True
    # Snapshot only AFTER the live audit above has read `inbox.played` — never before.
    observed_commitments = dict(inbox.played)
    final_outcome, _ = settled_outcome(terminal, audits_present=audits_present, audits_passed=audit_ok)
    row = SeriesRow(
        sub_game_number=sub_game,
        role=role,
        outcome=final_outcome,
        steps=len(our_records),
        score_police=score_for(final_outcome, Role.POLICE),
        score_thief=score_for(final_outcome, Role.THIEF),
        audit_ok=audit_ok,
    )
    if evidence_sink is not None:
        evidence_sink(
            capture_subgame_evidence(
                sub_game_index=sub_game,
                terms=terms,
                own_records_raw=audit["records"],
                opponent_records_raw=opponent_records_raw,
                observed_opponent_commitments=observed_commitments,
                our_result_claim=terminal.value,
                opponent_result_claim=opponent_result_claim,
                row=row,
            )
        )
    return row


def _observe_once(applied: dict[int, dict], seen: set[int], engine: TurnEngine, step: int) -> None:
    """Observe an applied step exactly once — observe_opponent is not idempotent."""
    if step in seen:
        return
    seen.add(step)
    engine.observe_opponent(applied[step])


def _our_move(engine, role: Role, is_thief: bool, lap: int, sub_game: int) -> tuple[dict, dict]:
    """Ask the engine for a move; return (turn message, sealed record)."""
    return seal_turn(engine.decide(), role, is_thief, lap)
