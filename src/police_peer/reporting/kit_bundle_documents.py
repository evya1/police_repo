"""Document-shaping helpers for league-kit bundle projection."""

from __future__ import annotations

import json

from common.transport.kit_records import build_summary
from common.transport.league_kit_envelope import wrap_outbound_records


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
        "skipped": False,
        "verified_steps": len(evidence.own_records),
        "failed_steps": [],
    }
    return build_summary(
        sub_game_number=number, our_group=ours, our_role=row.role.value,
        opponent_group=theirs, result=row.outcome.value, winner_group=winner,
        steps=row.steps, audit=audit,
    )
