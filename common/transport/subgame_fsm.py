"""State-machine-driven subgame driver — the selectable alternative to `play_subgame`.

Same batch wire protocol (D3), same helpers (D4), same failure behavior (D5). The only
differences from `play_subgame` are the ``PeerStateMachine`` threaded through the phases —
a guard that rejects illegal phase orderings — and the resulting ``history`` (replay hook,
D7). Default OFF: `series.PeerFacade` selects this driver only when `subgame_driver` is passed.
"""

from __future__ import annotations

from common.domain.scoring import Outcome, Role, role_for, score_for, settled_outcome
from common.transport.audit import audit_records
from common.transport.inbox import Inbox
from common.transport.series import LAPS_PER_SUBGAME, PeerConfig, SeriesRow, TurnEngine
from common.transport.state import PeerState, PeerStateMachine
from common.transport.subgame import _audit_payload, _our_move, _wait_audit, _wait_for_step


def play_subgame_fsm(channel, engine: TurnEngine, config: PeerConfig, sub_game: int) -> SeriesRow:
    """Play one sub-game exactly as `play_subgame` does, machine-guarded (D2).

    One ring per sub-game: the batch loop fuses compute + seal + send per lap, so
    ``COMPUTING_MOVE`` and ``COMMITTING`` are entered adjacently before it.
    """
    role = role_for(config.natural_role, sub_game)
    is_thief = role is Role.THIEF
    inbox = Inbox()
    applied: dict[int, dict] = {}
    our_records: list[dict] = []
    machine = PeerStateMachine()

    # WAITING_FOR_OPPONENT — the police honours thief-first (FR-18).
    if not is_thief:
        _wait_for_step(channel, inbox, applied, 1, config.budgets)

    machine.to(PeerState.COMPUTING_MOVE)
    machine.to(PeerState.COMMITTING)
    for lap in range(1, LAPS_PER_SUBGAME + 1):
        message, record = _our_move(engine, role, is_thief, lap, sub_game)
        channel.send_turn(message)
        our_records.append(record)

    # AWAITING_REVEAL — every commit of ours is in flight; wait for the opponent's final move.
    machine.to(PeerState.AWAITING_REVEAL)
    flush = getattr(channel, "flush", None)
    if flush is not None:
        flush()
    _wait_for_step(channel, inbox, applied, LAPS_PER_SUBGAME, config.budgets)

    # VERIFYING — mutual audit exchange.
    machine.to(PeerState.VERIFYING)
    terminal = Outcome.SURVIVAL if is_thief else Outcome.CAPTURE
    channel.send_audit(_audit_payload(role, our_records, terminal))
    opponent_audit = _wait_audit(channel, config.budgets)
    if opponent_audit is None:
        audit_ok, audits_present = False, False
    else:
        result = audit_records(opponent_audit.get("records", []), inbox.played, config.terms)
        audit_ok, audits_present = result.passed, True

    machine.to(PeerState.WAITING_FOR_OPPONENT)  # settled; next sub-game gets a fresh machine
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
