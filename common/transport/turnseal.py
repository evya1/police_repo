"""Commit-Reveal sealing for one half-turn, and the sealed game-ending final.

Split out of ``subgame.py`` so that module owns only the exchange loop and this one owns
the record shape: how a decision becomes a public message plus a private sealed record,
and how the settling peer seals the final step it still owes (rules 35, 46/47).
"""

from __future__ import annotations

from datetime import UTC, datetime

from common.domain.scoring import Outcome, Role
from common.transport.canonical import commit as hash_commit
from common.transport.integrity import new_nonce
from common.transport.state import PeerState

#: The keys a sealed record projects onto the wire — everything else stays local.
PUBLIC_TURN_KEYS = frozenset({
    "step", "sender", "hint", "smell_grid", "barrier_placed",
    "capture_claim", "claim_response", "win_claim", "timestamp",
})


def seal_turn(decision: dict, role: Role, is_thief: bool, step: int,
              sub_game: int = 1) -> tuple[dict, dict]:
    """Seal a decision into (public turn message, sealed record).

    The sealed record follows the reference-v3 audit wire: ``{payload, nonce, commit}``
    where ``commit`` binds the nested ``payload`` (reference ``audit_records`` re-hashes
    ``payload`` and compares against ``commit``). The public ``message`` stays flat and
    unchanged — that is the reference-v3 ``TurnMessage`` surface.
    """
    nonce = new_nonce()
    payload = dict(decision)
    payload["step"] = step
    payload["sender"] = role.value
    payload["role"] = role.value          # reference-v3 records name the role inside payload
    payload["sub_game"] = sub_game
    payload["intent"] = "evade" if is_thief else "chase"
    payload["timestamp"] = datetime.now(UTC).isoformat()

    commit = hash_commit(payload, nonce)
    record = {"payload": payload, "nonce": nonce, "commit": commit}

    message = {key: payload[key] for key in PUBLIC_TURN_KEYS if key in payload}
    message["commit"] = commit
    return message, record


def terminal_final(engine, role: Role, is_thief: bool, step: int) -> tuple[dict, dict] | None:
    """The sealed game-ending final, or None if this engine owes none."""
    fn = getattr(engine, "terminal_final", None)
    if fn is None:
        return None
    payload = fn()
    return None if payload is None else seal_turn(payload, role, is_thief, step)


def settle_final(
    channel, machine, engine, role: Role, is_thief: bool, step: int,
    our_records: list[dict], flush,
) -> None:
    """Send the settled final step (COMPUTING_MOVE -> COMMITTING from WAITING_FOR_OPPONENT)."""
    final = terminal_final(engine, role, is_thief, step)
    if final is None:
        return
    machine.to(PeerState.COMPUTING_MOVE)
    machine.to(PeerState.COMMITTING)
    message, record = final
    channel.send_turn(message)
    our_records.append(record)
    if flush is not None:
        flush()


def audit_payload(role: Role, our_records: list[dict], terminal: Outcome) -> dict:
    """Seal the step-0 identity record and pack our audit payload (FR-19, FR-42)."""
    nonce = new_nonce()
    step0_payload = {"step": 0, "sender": role.value, "role": role.value, "intent": "declare"}
    step0 = {"payload": step0_payload, "nonce": nonce,
             "commit": hash_commit(step0_payload, nonce)}
    records = [step0] + our_records
    return {
        # reference-v3 audit wire: sender + records + result_claim (SPEC §7.5).
        # ``sender`` is required by the opponent's AuditPayload.from_wire; ``nonces``
        # is our own extra that a conformant receiver tolerates (unknown keys pass).
        "sender": role.value,
        "records": records,
        "nonces": [r["nonce"] for r in records],
        "result_claim": terminal.value,
    }
