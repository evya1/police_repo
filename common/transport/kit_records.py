"""The record-envelope guard and the per-sub-game summary block (CT-07, ADR-012).

Split out of ``kit_documents`` so both stay inside the 150-logical-line rule. These two pieces
belong together: they are the parts of a log artifact that describe the EVIDENCE, while
``kit_documents`` owns the envelopes that carry it.

Nothing here hashes anything. ``_RECORD_KEYS`` is the whole contract: a record reaching a kit
log must already be ``{"payload": ..., "nonce": ..., "commit": ...}``. Our internal shape is
flat -- ``{**payload, "nonce": ..., "commit": ...}`` -- and handing that to the kit's auditor
is precisely what made every honest log read as tampered, because the auditor looks for
``record["payload"]`` and finds nothing to re-hash. The wrap belongs to
``league_kit_envelope.wrap_outbound_records``; this module only refuses what skipped it.
"""

from __future__ import annotations

#: The envelope keys every sealed record must carry once wrapped for the kit's audit.
RECORD_KEYS = frozenset({"payload", "nonce", "commit"})


class KitDocumentError(Exception):
    """Evidence cannot produce a well-formed kit artifact."""


def check_records(records: object, half: str) -> list[dict]:
    """Return ``records`` unchanged, or refuse anything not already wrapped for the kit."""
    if not isinstance(records, list):
        raise KitDocumentError(f"{half} records must be a list, got {type(records).__name__}")
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise KitDocumentError(f"{half} record {index} is not an object")
        missing = sorted(RECORD_KEYS - set(record))
        if missing:
            raise KitDocumentError(
                f"{half} record {index} is missing {missing} -- records must already be wrapped "
                f"by league_kit_envelope.wrap_outbound_records before reaching this builder; "
                f"this builder never wraps and never re-hashes"
            )
        if not isinstance(record["payload"], dict):
            raise KitDocumentError(f"{half} record {index} has a non-object payload")
    return records


def build_summary(
    *,
    sub_game_number: int,
    our_group: str,
    our_role: str,
    opponent_group: str,
    result: str,
    winner_group: str | None,
    steps: int,
    audit: dict,
) -> dict:
    """Build the per-sub-game summary block a log carries beside its records."""
    return {
        "sub_game_number": sub_game_number,
        "group_id": our_group,
        "role": our_role,
        "opponent_group_id": opponent_group,
        "result": result,
        "winner_group": winner_group,
        "steps": steps,
        "audit": audit,
    }
