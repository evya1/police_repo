"""Document-shaping helpers for league-kit bundle projection."""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from common.transport.kit_records import build_summary
from common.transport.league_kit_envelope import wrap_outbound_records

ISRAEL_TIMEZONE = ZoneInfo("Asia/Jerusalem")


def records(sealed) -> list[dict]:
    """Decode sealed records and wrap them in the kit's audit envelope."""
    flat = [
        {**json.loads(record.payload_bytes), "nonce": record.nonce, "commit": record.commitment}
        for record in sealed
    ]
    return wrap_outbound_records(flat)


def document_bytes(document: dict) -> bytes:
    """Return readable UTF-8 JSON with an explicit final newline."""
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode()


def summary(evidence, row, *, number: int, ours: str, theirs: str, winner: str | None) -> dict:
    """Build one kit log summary from sealed evidence and its settled ledger row."""
    audit = {
        "passed": bool(row.audit_ok),
        "verified_steps": len(evidence.own_records),
        "failed_steps": [],
    }
    timestamps = []
    for sealed in (*evidence.own_records, *evidence.opponent_records):
        value = json.loads(sealed.payload_bytes).get("timestamp")
        if isinstance(value, str):
            timestamps.append(value)
    if not timestamps:
        raise ValueError(f"sub-game {number} has no sealed timestamps")
    parsed = sorted(datetime.fromisoformat(value) for value in timestamps)
    start = parsed[0].astimezone(ISRAEL_TIMEZONE)
    end = parsed[-1].astimezone(ISRAEL_TIMEZONE)
    result = build_summary(
        sub_game_number=number, our_group=ours, our_role=row.role.value,
        opponent_group=theirs, result=row.outcome.value, winner_group=winner,
        steps=row.steps, audit=audit,
    )
    winner_role = None
    if winner == ours:
        winner_role = row.role.value
    elif winner == theirs:
        winner_role = "thief" if row.role.value == "police" else "police"
    result["winner_role"] = winner_role
    result.pop("winner_group")
    result.update({
        "timezone": "Asia/Jerusalem", "started_at": start.isoformat(),
        "ended_at": end.isoformat(), "duration_seconds": max(0.0, (end - start).total_seconds()),
    })
    return result
